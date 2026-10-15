"""Database lifecycle safety: pre-update snapshots, module updates, restore tests.

Everything that touches Docker or Postgres goes through names imported at module level
(`backup_database`, `_connect`, `exec_in_container`, `subprocess`) so the tests can fake
the boundary.
"""
import os
import re
import subprocess
import time

from django.conf import settings
from psycopg2 import sql

from .db_service import (_check_db_name, _connect, _db_endpoint, _db_password, backup_database)
from .docker_service import exec_in_container

SAFE_ARG = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.,-]{0,127}$')
SNAPSHOT_PREFIX = 'pre-update-'
SCRATCH_PREFIX = 'zz-restore-test-'


def database_size_mb(db_port, dbname):
    _check_db_name(dbname)
    conn = _connect(db_port)
    try:
        cur = conn.cursor()
        cur.execute('SELECT pg_database_size(%s)', (dbname,))
        return int(cur.fetchone()[0]) // (1024 * 1024)
    finally:
        conn.close()


# ── pre-update snapshot ────────────────────────────────────────────────────
def snapshot_before_update(project, db_port, dbname, backup_dir, max_mb=500, keep=3):
    """Dump the database before a module update so a bad update can be undone.
    Returns the snapshot path, or None when the database is too big to do this automatically."""
    _check_db_name(dbname)
    if database_size_mb(db_port, dbname) > max_mb:
        return None
    path, name = backup_database(db_port, dbname, backup_dir)
    target = os.path.join(backup_dir, SNAPSHOT_PREFIX + name)
    os.replace(path, target)
    mine = sorted((f for f in os.listdir(backup_dir) if f.startswith(f'{SNAPSHOT_PREFIX}{dbname}-')),
                  key=lambda f: os.path.getmtime(os.path.join(backup_dir, f)), reverse=True)
    for stale in mine[keep:]:
        os.remove(os.path.join(backup_dir, stale))
    return target


# ── module update ──────────────────────────────────────────────────────────
def _lines(chunk):
    text = chunk if isinstance(chunk, str) else chunk.decode('utf-8', errors='replace')
    return [l.rstrip() for l in text.splitlines() if l.strip()]


def run_module_update(project, db_port, dbname, module, emit, backup_dir, snapshot=True, max_snapshot_mb=500):
    """Update a module (or comma-separated modules) in one database. Returns 0 on success."""
    if not SAFE_ARG.match(module or '') or not SAFE_ARG.match(dbname or '') or not SAFE_ARG.match(project or ''):
        emit('Refused: unsafe database or module name.')
        return 2
    if snapshot:
        emit('Taking a safety snapshot before updating…')
        try:
            path = snapshot_before_update(project, db_port, dbname, backup_dir, max_mb=max_snapshot_mb)
        except Exception as e:                       # never update without the promised safety net
            emit(f'Snapshot failed ({e}). Update aborted; nothing was changed.')
            return 3
        emit(f'Snapshot saved: {os.path.basename(path)}' if path else
             f'Snapshot skipped: database is larger than {max_snapshot_mb} MB (take a manual backup if needed).')
    cmd = ['odoo', '-c', '/etc/odoo/odoo.conf', '-d', dbname, '-u', module,
           '--stop-after-init', '--no-http', '--max-cron-threads=0', '--workers=0']
    _code, output = exec_in_container(f'{project}-app', cmd)
    failed = False
    for chunk in output:
        for line in _lines(chunk):
            emit(line)
            if ' CRITICAL ' in line or line.startswith('Traceback'):
                failed = True
    return 1 if failed else 0


# ── restore test ───────────────────────────────────────────────────────────
def latest_backup(backup_dir):
    """Newest real backup (pre-update snapshots are not backups) or None."""
    try:
        files = [os.path.join(backup_dir, f) for f in os.listdir(backup_dir)
                 if f.endswith('.dump') and not f.startswith(SNAPSHOT_PREFIX)]
    except OSError:
        return None
    return max(files, key=os.path.getmtime) if files else None


def _inside(path, directory):
    real, root = os.path.realpath(path), os.path.realpath(directory)
    return real.startswith(root + os.sep)


def restore_check(project, db_port, backup_path, backup_dir):
    """Restore a backup into a scratch database, sanity-check it, always drop it."""
    if not _inside(backup_path, backup_dir) or not os.path.isfile(backup_path):
        raise ValueError('backup file must be inside the project backup directory')
    scratch = f'{SCRATCH_PREFIX}{project}-{int(time.time())}'[:63]
    _check_db_name(scratch)
    started = time.time()
    result = {'ok': False, 'checks': {}, 'seconds': 0.0, 'error': '', 'scratch': scratch}

    def _admin(statement_builder):
        conn = _connect(db_port)
        try:
            conn.autocommit = True
            cur = conn.cursor()
            statement_builder(cur)
        finally:
            conn.close()

    try:
        _admin(lambda cur: cur.execute(sql.SQL('CREATE DATABASE {} OWNER {}').format(
            sql.Identifier(scratch), sql.Identifier(settings.DB_USER))))
        host, port = _db_endpoint(db_port)
        env = {**os.environ, 'PGPASSWORD': _db_password(db_port)}
        r = subprocess.run(['pg_restore', '-h', host, '-p', str(port), '-U', settings.DB_USER,
                            '-d', scratch, '--no-owner', '--no-acl', backup_path],
                           capture_output=True, text=True, env=env, timeout=900)
        # pg_restore exits 1 for ignorable per-object errors too; only a failure to connect or
        # read the archive is fatal here. Whether the data really came back is decided by the
        # sanity checks below.
        if r.returncode != 0 and re.search(r'connection to server|could not connect|FATAL|No such file|'
                                           r'not a valid archive|input file', r.stderr or '', re.I):
            result['error'] = (r.stderr or 'pg_restore failed')[:500]
            return result
        conn = _connect(db_port, scratch)
        try:
            cur = conn.cursor()
            cur.execute('SELECT count(*) FROM res_users')
            users = int(cur.fetchone()[0])
            cur.execute("SELECT count(*) FROM ir_module_module WHERE state = 'installed'")
            modules = int(cur.fetchone()[0])
        finally:
            conn.close()
        result['checks'] = {'users': users, 'modules': modules}
        result['ok'] = users > 0 and modules > 0
        if not result['ok']:
            result['error'] = 'restored database is empty (no users or no installed modules)'
        return result
    except Exception as e:
        result['error'] = str(e)[:500]
        return result
    finally:
        result['seconds'] = round(time.time() - started, 1)
        try:
            _admin(lambda cur: (
                cur.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s", (scratch,)),
                cur.execute(sql.SQL('DROP DATABASE IF EXISTS {}').format(sql.Identifier(scratch)))))
        except Exception:
            pass


def run_restore_tests(projects, backup_root, record):
    """Restore-test the latest backup of every project. One failure never stops the others."""
    results = []
    for p in projects:
        name = p['name']
        directory = os.path.join(backup_root, name)
        path = latest_backup(directory)
        if not path:
            results.append({'project': name, 'status': 'no-backup'})
            continue
        try:
            outcome = restore_check(name, p['db_port'], path, directory)
        except Exception as e:
            outcome = {'ok': False, 'error': str(e), 'checks': {}, 'seconds': 0}
        record(name, outcome)
        results.append({'project': name, 'status': 'ok' if outcome['ok'] else 'failed',
                        'backup': os.path.basename(path), **{k: outcome.get(k) for k in ('checks', 'seconds', 'error')}})
    return results
