import base64
import hashlib
import hmac
import json
import time

from odoo import api, models, tools
from odoo.exceptions import AccessDenied

_MAX_TTL = 120          # seconds a link may live, whatever the dashboard asks for
_PREFIX = 'dashsso:'    # carries the token through the Odoo 17 "password" argument


def _sso_key():
    """Per-project HMAC key derived from the project's (random, otherwise unused)
    Odoo master password, so no extra secret has to be distributed."""
    master = tools.config.get('admin_passwd') or ''
    if len(master) < 16:   # never accept a weak/default master password as key material
        return None
    return hashlib.sha256(('dashboard-sso:' + master).encode()).digest()


def _verify(token, login, dbname):
    key = _sso_key()
    if not key or not token or '.' not in token:
        return None
    body, _, sig = token.rpartition('.')
    expected = hmac.new(key, body.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(body + '=' * (-len(body) % 4)))
    except Exception:
        return None
    now = time.time()
    if payload.get('db') != dbname or payload.get('login') != login:
        return None
    # Allow a small clock skew into the future. Age is bounded by exp, not iat:
    # registry startup and browser navigation can take more than five seconds.
    if not (payload.get('iat', 0) <= now + 5 and payload.get('exp', 0) >= now
            and 0 < payload['exp'] - payload['iat'] <= _MAX_TTL):
        return None
    return payload


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _dashboard_sso_consume(self, token):
        """Validate + burn the one-time token. True only for a fresh, valid link."""
        self.ensure_one()
        payload = _verify(token, self.login, self.env.cr.dbname)
        if not payload or not payload.get('n'):
            return False
        cr = self.env.cr
        cr.execute("""CREATE TABLE IF NOT EXISTS dashboard_login_nonce
                      (nonce varchar PRIMARY KEY, created timestamp DEFAULT now())""")
        cr.execute("DELETE FROM dashboard_login_nonce WHERE created < now() - interval '1 day'")
        cr.execute("INSERT INTO dashboard_login_nonce (nonce) VALUES (%s) "
                   "ON CONFLICT DO NOTHING RETURNING nonce", (payload['n'],))
        return bool(cr.fetchone())

    def _check_credentials(self, credential, env):
        token = None
        if isinstance(credential, dict):           # Odoo 18+
            if credential.get('type') == 'dashboard_sso':
                token = credential.get('token')
                if not self._dashboard_sso_consume(token):
                    raise AccessDenied()
                return {'uid': self.env.user.id, 'auth_method': 'dashboard_sso', 'mfa': 'default'}
        elif isinstance(credential, str) and credential.startswith(_PREFIX):   # Odoo 17
            if not self._dashboard_sso_consume(credential[len(_PREFIX):]):
                raise AccessDenied()
            return None
        return super()._check_credentials(credential, env)
