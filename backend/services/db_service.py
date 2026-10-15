import os
import re
import secrets
import subprocess
from datetime import datetime
import psycopg2
from psycopg2 import sql
from django.conf import settings

from .docker_service import exec_in_container_sync, get_docker_client
from .registry import read_registry


_DB_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,62}$')


def _check_db_name(name):
    """Database names reach SQL identifiers, pg_dump/pg_restore args and file names."""
    if not isinstance(name, str) or not _DB_NAME.match(name):
        raise ValueError(f'invalid database name: {name!r}')
    return name


def _db_endpoint(db_port):
    """Resolve a project's registry ``db_port`` to a direct ``(host, port)``.

    The project Postgres containers are reachable by container name
    (``<project>-db``) on the shared ``odoo-dbnet`` docker network, on the
    internal port 5432 — they are no longer published to the host bridge.
    Falls back to ``settings.DB_HOST`` + the given port if the project can't
    be resolved (registry missing, tests, ad-hoc port).
    """
    try:
        for p in read_registry():
            if str(p.get('db_port')) == str(db_port):
                return f"{p['name']}-db", 5432
    except Exception:
        pass
    return settings.DB_HOST, int(db_port)


SECRETS_DIR = os.path.join(settings.ODOO_DEV_BASE, 'secrets')


def project_password(project_name):
    """Per-project Postgres password from secrets/<project>.pgpass (the same file the
    Odoo container mounts as ~/.pgpass); falls back to the legacy shared password."""
    try:
        with open(os.path.join(SECRETS_DIR, f'{project_name}.pgpass')) as f:
            line = f.readline().strip()
        # host:port:database:user:password — password may contain escaped ':' or '\\'
        return re.sub(r'\\(.)', r'\1', line.split(':', 4)[4])
    except (OSError, IndexError):
        return settings.DB_PASSWORD


def _db_password(db_port):
    try:
        for p in read_registry():
            if str(p.get('db_port')) == str(db_port):
                return project_password(p['name'])
    except Exception:
        pass
    return settings.DB_PASSWORD


def _connect(db_port, dbname='postgres'):
    host, port = _db_endpoint(db_port)
    return psycopg2.connect(
        host=host,
        port=port,
        user=settings.DB_USER,
        password=_db_password(db_port),
        dbname=dbname,
        connect_timeout=5,
    )


def list_databases(db_port):
    try:
        conn = _connect(db_port)
        cur = conn.cursor()
        cur.execute("""
            SELECT datname,
                   pg_size_pretty(pg_database_size(datname)) AS size,
                   pg_database_size(datname) AS size_bytes
            FROM pg_database
            WHERE datname NOT IN ('postgres', 'template0', 'template1')
            ORDER BY datname
        """)
        rows = cur.fetchall()
        conn.close()
        return [{'name': r[0], 'size': r[1], 'size_bytes': r[2]} for r in rows]
    except Exception as e:
        return {'error': str(e)}


def backup_database(db_port, dbname, backup_dir):
    _check_db_name(dbname)
    os.makedirs(backup_dir, exist_ok=True)
    ts = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
    filename = f'{dbname}-{ts}.dump'
    filepath = os.path.join(backup_dir, filename)
    host, port = _db_endpoint(db_port)
    env = {**os.environ, 'PGPASSWORD': _db_password(db_port)}
    result = subprocess.run(
        ['pg_dump', '-h', host, '-p', str(port),
         '-U', settings.DB_USER, '-F', 'c', '-f', filepath, dbname],
        capture_output=True, text=True, env=env, timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or 'pg_dump failed')
    return filepath, filename


def database_state(db_port, dbname):
    """Is this database neutralized? Odoo records database.is_neutralized when it is."""
    _check_db_name(dbname)
    conn = _connect(db_port, dbname)
    try:
        cur = conn.cursor()
        cur.execute("SELECT value FROM ir_config_parameter WHERE key = 'database.is_neutralized'")
        row = cur.fetchone()
        return {'neutralized': bool(row) and str(row[0]).lower() in ('true', '1')}
    finally:
        conn.close()


def lock_down_database(db_port, dbname):
    """Only the owning role (and superusers) may connect: no PUBLIC access to a developer copy."""
    _check_db_name(dbname)
    conn = _connect(db_port)
    try:
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(sql.SQL('REVOKE CONNECT ON DATABASE {} FROM PUBLIC').format(sql.Identifier(dbname)))
    finally:
        conn.close()


def restore_database(db_port, dbname, backup_filepath, project_name=None):
    """Restore a .dump file into dbname (drops and recreates), then neutralize it."""
    _check_db_name(dbname)
    # Drop existing connections and database
    try:
        conn = _connect(db_port)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = %s AND pid <> pg_backend_pid()
        """, (dbname,))
        cur.execute(sql.SQL('DROP DATABASE IF EXISTS {}').format(sql.Identifier(dbname)))
        cur.execute(sql.SQL('CREATE DATABASE {} OWNER {}').format(
            sql.Identifier(dbname), sql.Identifier(settings.DB_USER)))
        conn.close()
    except Exception as e:
        raise RuntimeError(f'Failed to prepare database: {e}')

    host, port = _db_endpoint(db_port)
    env = {**os.environ, 'PGPASSWORD': _db_password(db_port)}
    result = subprocess.run(
        ['pg_restore', '-h', host, '-p', str(port),
         '-U', settings.DB_USER, '-d', dbname, '--no-owner', '--no-acl', backup_filepath],
        capture_output=True, text=True, env=env, timeout=600,
    )
    if result.returncode != 0 and result.stderr:
        # pg_restore exits non-zero even on warnings; only raise if stderr looks fatal
        if 'ERROR' in result.stderr and 'warning' not in result.stderr.lower():
            raise RuntimeError(result.stderr)

    if project_name:
        neutralize_database(project_name, dbname, db_port=db_port)
    lock_down_database(db_port, dbname)


def list_backup_files(project, backup_dir):
    files = []
    try:
        entries = sorted(os.listdir(backup_dir), reverse=True)
    except (OSError, FileNotFoundError):
        return []
    for fname in entries:
        if fname.endswith('.dump'):
            fpath = os.path.join(backup_dir, fname)
            try:
                stat = os.stat(fpath)
            except (OSError, FileNotFoundError):
                continue
            files.append({
                'filename': fname,
                'size_bytes': stat.st_size,
                'size': _human_size(stat.st_size),
                'modified': datetime.utcfromtimestamp(stat.st_mtime).isoformat(),
            })
    return files


def _human_size(b):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if b < 1024:
            return f'{b:.1f} {unit}'
        b /= 1024
    return f'{b:.1f} TB'


def duplicate_database(db_port, src, dst, project_name=None):
    _check_db_name(src)
    _check_db_name(dst)
    conn = _connect(db_port)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("""
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = %s AND pid <> pg_backend_pid()
    """, (src,))
    cur.execute(sql.SQL('CREATE DATABASE {} TEMPLATE {}').format(
        sql.Identifier(dst), sql.Identifier(src)))
    conn.close()

    if project_name:
        neutralize_database(project_name, dst, db_port=db_port)
    lock_down_database(db_port, dst)


def neutralize_database(project_name, dbname, db_port=None):
    _check_db_name(dbname)
    _check_db_name(project_name)
    """Run Odoo's built-in neutralize command against dbname inside <project>-app.

    Disables outgoing mail servers, cron jobs, payment providers, and other
    production-facing integrations so a demo/staging copy can't act on the outside
    world. Mandatory after any restore or duplicate that creates a new database.
    """
    exit_code, output = exec_in_container_sync(
        f'{project_name}-app',
        f'odoo neutralize -c /etc/odoo/odoo.conf -d {dbname}',
    )
    if exit_code != 0:
        detail = output.decode(errors='replace') if isinstance(output, bytes) else output
        raise RuntimeError(f'Neutralize failed: {detail}')
    if db_port is not None and not database_state(db_port, dbname)['neutralized']:
        # the command exited 0 but Odoo did not record the flag: do not hand the database out
        raise RuntimeError(f'{dbname} is not neutralized: Odoo did not record database.is_neutralized')


def drop_database(db_port, dbname):
    _check_db_name(dbname)
    conn = _connect(db_port)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("""
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = %s AND pid <> pg_backend_pid()
    """, (dbname,))
    cur.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(dbname)))
    conn.close()


def _parse_volume_mappings(compose_path, odoo_dev_base):
    if not os.path.exists(compose_path):
        return {}
    compose_dir = os.path.dirname(os.path.abspath(compose_path))
    with open(compose_path) as f:
        content = f.read()
    host_home = os.path.dirname(odoo_dev_base)
    content = content.replace('${HOME}', host_home).replace('$HOME', host_home)
    content = content.replace('${ODOO_DEV_BASE}', odoo_dev_base)
    mappings = {}
    for m in re.finditer(r'^\s*-\s+([^:]+):(/[^:\s]+)', content, re.MULTILINE):
        host = m.group(1).strip()
        container = m.group(2).strip()
        if container.startswith('/mnt/'):
            if not os.path.isabs(host):
                host = os.path.normpath(os.path.join(compose_dir, host))
            mappings[container] = host
    return mappings


def _scan_modules(host_path):
    modules = set()
    if not os.path.isdir(host_path):
        return modules
    try:
        for entry in os.scandir(host_path):
            if entry.is_dir() and os.path.exists(os.path.join(entry.path, '__manifest__.py')):
                modules.add(entry.name)
    except OSError:
        pass
    return modules


def _resolve_host_path(container_path, vol_mappings):
    if container_path in vol_mappings:
        return vol_mappings[container_path]
    for cp, hp in vol_mappings.items():
        if container_path.startswith(cp + '/'):
            return hp + container_path[len(cp):]
    return None


def _find_compose_path(odoo_dev_base, folder=None, version=None):
    """Locate the docker-compose.yml for a project.

    Search strategy:
    1. Walk up from {odoo_dev_base}/{folder} looking for docker-compose.yml.
    2. Try {odoo_dev_base}/v{version}/docker-compose.yml.
    3. Return None if not found.
    """
    if folder:
        candidate = os.path.join(odoo_dev_base, folder)
        while candidate and candidate != odoo_dev_base and candidate != '/':
            compose = os.path.join(candidate, 'docker-compose.yml')
            if os.path.exists(compose):
                return compose
            candidate = os.path.dirname(candidate)

    if version:
        versioned = os.path.join(odoo_dev_base, f'v{version}', 'docker-compose.yml')
        if os.path.exists(versioned):
            return versioned

    return None


def list_modules_grouped(db_port, dbname, project_name, odoo_dev_base, folder=None, version=None):
    from .git_service import get_addons_path
    try:
        conn = _connect(db_port, dbname)
        cur = conn.cursor()
        cur.execute("""
            SELECT name, state, latest_version, author
            FROM ir_module_module
            WHERE state IN ('installed', 'to upgrade', 'to remove', 'uninstalled')
            ORDER BY name
        """)
        rows = cur.fetchall()
        conn.close()
    except Exception as e:
        return {'error': str(e)}

    all_modules = [{'name': r[0], 'state': r[1], 'version': r[2], 'author': r[3]} for r in rows]
    addons_entries = get_addons_path(project_name, folder, version=version)
    compose_path = _find_compose_path(odoo_dev_base, folder=folder, version=version)
    vol_mappings = _parse_volume_mappings(compose_path, odoo_dev_base) if compose_path else {}

    module_to_source = {}
    for entry in addons_entries:
        cpath = entry['path']
        if cpath.startswith('/usr/') or 'dist-packages' in cpath or 'site-packages' in cpath:
            continue
        host_path = _resolve_host_path(cpath, vol_mappings)
        if not host_path:
            continue
        for mod_name in _scan_modules(host_path):
            if mod_name not in module_to_source:
                module_to_source[mod_name] = entry

    groups = {}
    core_modules = []
    for mod in all_modules:
        source = module_to_source.get(mod['name'])
        if source:
            key = source['label']
            if key not in groups:
                groups[key] = {'label': key, 'kind': source['kind'], 'path': source['path'], 'modules': []}
            groups[key]['modules'].append(mod)
        else:
            core_modules.append(mod)

    ordered = []
    seen = set()
    for entry in addons_entries:
        lbl = entry['label']
        if lbl in groups and lbl not in seen:
            ordered.append(groups[lbl])
            seen.add(lbl)

    if core_modules:
        ordered.insert(0, {'label': 'Odoo Core', 'kind': 'core', 'path': '/usr/lib/\u2026/odoo/addons', 'modules': core_modules})

    return {'groups': ordered}


# ── Odoo database lifecycle without shared passwords ─────────────────────
#
# Odoo's own database manager needs the master password. The dashboard does
# the same operations directly in Postgres as the logged-in user (audited),
# so nobody needs to know or share the master password. These helpers create
# a database and set an individual, random, shown-once admin login.

_LOGIN = re.compile(r'^[A-Za-z0-9_.@+-]{1,64}$')


def _hash_odoo_password(project_name, password):
    """pbkdf2 hash computed inside the project's own Odoo container (passlib is
    already there), the password is passed via environment, never argv."""
    container = get_docker_client().containers.get(f'{project_name}-app')
    code = ("import os\nfrom passlib.context import CryptContext\n"
            "print(CryptContext(['pbkdf2_sha512'], pbkdf2_sha512__rounds=600000)"
            ".hash(os.environ['PW']))")
    res = container.exec_run(['python3', '-c', code], environment={'PW': password}, demux=False)
    lines = (res.output or b'').decode(errors='replace').strip().splitlines()
    hashed = lines[-1].strip() if lines else ''
    if res.exit_code != 0 or not hashed.startswith('$pbkdf2-sha512$'):
        raise RuntimeError('could not compute the password hash inside the project container')
    return hashed


def set_odoo_user_password(project_name, db_port, dbname, login='admin'):
    """Set a fresh random password for an Odoo user and return it (shown once)."""
    _check_db_name(dbname)
    if not isinstance(login, str) or not _LOGIN.match(login):
        raise ValueError('invalid login')
    password = secrets.token_urlsafe(18)
    hashed = _hash_odoo_password(project_name, password)
    conn = _connect(db_port, dbname)
    try:
        cur = conn.cursor()
        cur.execute('UPDATE res_users SET password = %s WHERE login = %s AND active', (hashed, login))
        if cur.rowcount != 1:
            raise LookupError(f'no active user with login {login!r} in {dbname}')
        conn.commit()
    finally:
        conn.close()
    return password


def create_odoo_database(project_name, db_port, dbname, demo=False):
    """Initialise a brand-new Odoo database (base module) via the project's own
    container and give its admin user a random password. Returns (login, password)."""
    _check_db_name(dbname)
    _check_db_name(project_name)
    if dbname in list_database_names(db_port):
        raise ValueError(f'database {dbname!r} already exists')
    cmd = ['odoo', '-c', '/etc/odoo/odoo.conf', '-d', dbname, '-i', 'base', '--stop-after-init']
    if not demo:
        cmd.append('--without-demo=all')
    exit_code, output = exec_in_container_sync(f'{project_name}-app', cmd)
    if exit_code != 0:
        tail = (output.decode(errors='replace') if isinstance(output, bytes) else str(output))[-600:]
        raise RuntimeError(f'odoo initialisation failed: {tail}')
    # A brand-new database holds no live data or integrations; neutralizing it records that
    # fact (database.is_neutralized) so the access policy treats it like any dev copy.
    neutralize_database(project_name, dbname, db_port=db_port)
    lock_down_database(db_port, dbname)
    return 'admin', set_odoo_user_password(project_name, db_port, dbname, 'admin')


def list_database_names(db_port):
    result = list_databases(db_port)
    if isinstance(result, dict):  # {'error': ...}
        raise RuntimeError(result['error'])
    return [d['name'] for d in result]
