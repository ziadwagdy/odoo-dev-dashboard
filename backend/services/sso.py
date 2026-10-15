"""Signed, short-lived "log in as" links for the dashboard_login Odoo addon.

The HMAC key is derived from the project's Odoo master password (random and
otherwise unused now that databases are managed through the dashboard), exactly
as the addon derives it, so no extra secret has to be distributed or stored.
"""
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from urllib.parse import urlencode

from django.conf import settings

from .db_service import _connect, _check_db_name, exec_in_container_sync, database_state  # noqa: F401

LINK_TTL = 60  # seconds
_LOGIN = re.compile(r'^[A-Za-z0-9_.@+\-]{1,128}$')
ADDON = 'dashboard_login'


def _master_password(project):
    path = os.path.join(settings.ODOO_DEV_BASE, project['conf_file'] or f"{project['name']}/config/odoo.conf")
    with open(path) as f:
        m = re.search(r'(?m)^admin_passwd\s*=\s*(.+)$', f.read())
    master = m.group(1).strip() if m else ''
    if len(master) < 16:
        raise RuntimeError('project has no strong master password configured; refusing to sign links')
    return master


def _key(project):
    return hashlib.sha256(('dashboard-sso:' + _master_password(project)).encode()).digest()


def make_token(project, db, login, ttl=LINK_TTL):
    now = int(time.time())
    payload = {'db': db, 'login': login, 'iat': now, 'exp': now + min(ttl, 120), 'n': secrets.token_hex(12)}
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
    return body + '.' + hmac.new(_key(project), body.encode(), hashlib.sha256).hexdigest()


def list_login_candidates(db_port, db):
    """Active internal users of an Odoo database the dashboard user may sign in as."""
    _check_db_name(db)
    conn = _connect(db_port, db)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT u.login, COALESCE(p.name, u.login),
                   EXISTS (SELECT 1 FROM res_groups_users_rel r
                           JOIN ir_model_data d ON d.res_id = r.gid AND d.model = 'res.groups'
                                               AND d.module = 'base' AND d.name = 'group_system'
                           WHERE r.uid = u.id) AS is_admin
            FROM res_users u LEFT JOIN res_partner p ON p.id = u.partner_id
            WHERE u.active AND COALESCE(u.share, false) = false
            ORDER BY is_admin DESC, u.login LIMIT 300""")
        return [{'login': r[0], 'name': r[1], 'admin': bool(r[2])} for r in cur.fetchall()]
    finally:
        conn.close()


def _addon_state(db_port, db):
    conn = _connect(db_port, db)
    try:
        cur = conn.cursor()
        cur.execute("SELECT state FROM ir_module_module WHERE name = %s", (ADDON,))
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def ensure_addon_installed(project, db_port, db):
    """Install the tiny addon on first use (no data, one helper table)."""
    if _addon_state(db_port, db) == 'installed':
        return False
    exit_code, output = exec_in_container_sync(
        f"{project['name']}-app",
        ['odoo', '-c', '/etc/odoo/odoo.conf', '-d', db, '-i', ADDON, '--stop-after-init',
         '--workers=0', '--max-cron-threads=0', '--no-http', '--log-level=warn'])
    if exit_code != 0 or _addon_state(db_port, db) != 'installed':
        tail = (output.decode(errors='replace') if isinstance(output, bytes) else str(output))[-500:]
        raise RuntimeError(f'could not install {ADDON} (is /mnt/dashboard-addons mounted?): {tail}')
    return True


def build_login_url(project, db_port, db, login, redirect='/web'):
    _check_db_name(db)
    if not _LOGIN.match(login or ''):
        raise ValueError('invalid login')
    if login not in {u['login'] for u in list_login_candidates(db_port, db)}:
        raise LookupError(f'no active internal user {login!r} in {db}')
    ensure_addon_installed(project, db_port, db)
    host = project['url']
    q = urlencode({'db': db, 't': make_token(project, db, login), 'redirect': redirect})
    return f'https://{host}/dashboard/login?{q}'
