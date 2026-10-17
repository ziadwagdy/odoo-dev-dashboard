"""Find persistence planted inside Odoo databases (the incident's server actions, rogue admins, API keys).

Each database gets a silent baseline on its first scan; afterwards anything new alerts once.
Only ids and names are read, never code or key material.
"""
import logging

from apps.security.models import SeenItem
from .detection import Event

log = logging.getLogger(__name__)

_NOT_SHIPPED = "NOT IN (SELECT res_id FROM ir_model_data WHERE model = '{model}')"

QUERIES = {
    'code_action': "SELECT id, name FROM ir_act_server WHERE state = 'code' AND id " + _NOT_SHIPPED.format(model='ir.actions.server'),
    'system_user': ("SELECT u.id, u.login FROM res_users u JOIN res_groups_users_rel r ON r.uid = u.id "
                    "JOIN ir_model_data d ON d.res_id = r.gid AND d.model = 'res.groups' "
                    "AND d.module = 'base' AND d.name = 'group_system'"),
    'api_key': "SELECT id, name FROM res_users_apikeys",
    'python_cron': ("SELECT c.id, c.cron_name FROM ir_cron c JOIN ir_act_server a ON a.id = c.ir_actions_server_id "
                    "WHERE a.state = 'code' AND c.id " + _NOT_SHIPPED.format(model='ir.cron')),
}

LABELS = {
    'code_action': ('high', 'New server action with Python code'),
    'system_user': ('high', 'New administrator account'),
    'api_key': ('high', 'New API key'),
    'python_cron': ('high', 'New scheduled action running Python code'),
}


def _scan_db(project, db, fetch, handle):
    scope = f'{project}:{db}'
    first = not SeenItem.objects.filter(scope='baseline', kind='marker', item_id=scope).exists()
    for kind in QUERIES:
        try:
            rows = fetch(project, db, kind)
        except Exception as exc:                 # table missing on this version, or no access
            log.debug('persistence scan %s/%s skipped: %s', scope, kind, exc)
            continue
        known = set(SeenItem.objects.filter(scope=scope, kind=kind).values_list('item_id', flat=True))
        for item_id, label in rows:
            if str(item_id) in known:
                continue
            SeenItem.objects.get_or_create(scope=scope, kind=kind, item_id=str(item_id), defaults={'label': str(label)[:300]})
            if not first:
                severity, text = LABELS[kind]
                handle(Event(rule='odoo_persistence', severity=severity, source=scope,
                             key=f'persistence:{scope}:{kind}:{item_id}',
                             summary=f'{text} in {db} ({project}): {label}', sample=f'id={item_id}'))
    if first:
        SeenItem.objects.get_or_create(scope='baseline', kind='marker', item_id=scope)


def run_scan(projects, list_dbs, fetch, handle):
    for p in projects:
        try:
            dbs = list_dbs(p['db_port'])
        except Exception as exc:
            log.warning('persistence scan: cannot list databases of %s: %s', p['name'], exc)
            continue
        for db in dbs:
            try:
                _scan_db(p['name'], db, fetch, handle)
            except Exception:
                log.exception('persistence scan failed for %s:%s', p['name'], db)


def scan_all(handle):
    """Production wiring: every registered project, real databases."""
    from . import db_service
    from .registry import read_registry
    ports = {p['name']: p['db_port'] for p in read_registry()}

    def fetch(project, db, kind):
        conn = db_service._connect(ports[project], db)
        try:
            with conn.cursor() as cur:
                cur.execute(QUERIES[kind])
                return cur.fetchall()
        finally:
            conn.close()
    run_scan(read_registry(), db_service.list_database_names, fetch, handle)
