import os
import re
import subprocess
from datetime import datetime
import psycopg2
from django.conf import settings


def _connect(db_port, dbname='postgres'):
    return psycopg2.connect(
        host=settings.DB_HOST,
        port=int(db_port),
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
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
    os.makedirs(backup_dir, exist_ok=True)
    ts = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
    filename = f'{dbname}-{ts}.dump'
    filepath = os.path.join(backup_dir, filename)
    env = {**os.environ, 'PGPASSWORD': settings.DB_PASSWORD}
    result = subprocess.run(
        ['pg_dump', '-h', settings.DB_HOST, '-p', str(db_port),
         '-U', settings.DB_USER, '-F', 'c', '-f', filepath, dbname],
        capture_output=True, text=True, env=env, timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or 'pg_dump failed')
    return filepath, filename


def restore_database(db_port, dbname, backup_filepath):
    """Restore a .dump file into dbname (drops and recreates)."""
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
        cur.execute(f'DROP DATABASE IF EXISTS "{dbname}"')
        cur.execute(f'CREATE DATABASE "{dbname}" OWNER "{settings.DB_USER}"')
        conn.close()
    except Exception as e:
        raise RuntimeError(f'Failed to prepare database: {e}')

    env = {**os.environ, 'PGPASSWORD': settings.DB_PASSWORD}
    result = subprocess.run(
        ['pg_restore', '-h', settings.DB_HOST, '-p', str(db_port),
         '-U', settings.DB_USER, '-d', dbname, '--no-owner', '--no-acl', backup_filepath],
        capture_output=True, text=True, env=env, timeout=600,
    )
    if result.returncode != 0 and result.stderr:
        # pg_restore exits non-zero even on warnings; only raise if stderr looks fatal
        if 'ERROR' in result.stderr and 'warning' not in result.stderr.lower():
            raise RuntimeError(result.stderr)


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


def duplicate_database(db_port, src, dst):
    conn = _connect(db_port)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("""
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = %s AND pid <> pg_backend_pid()
    """, (src,))
    cur.execute(f'CREATE DATABASE "{dst}" TEMPLATE "{src}"')
    conn.close()


def drop_database(db_port, dbname):
    conn = _connect(db_port)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("""
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = %s AND pid <> pg_backend_pid()
    """, (dbname,))
    cur.execute(f'DROP DATABASE "{dbname}"')
    conn.close()


def _parse_volume_mappings(compose_path, odoo_dev_base):
    if not os.path.exists(compose_path):
        return {}
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


def list_modules_grouped(db_port, dbname, project_name, odoo_dev_base):
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
    addons_entries = get_addons_path(project_name)
    compose_path = os.path.join(odoo_dev_base, project_name, 'docker-compose.yml')
    vol_mappings = _parse_volume_mappings(compose_path, odoo_dev_base)

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
