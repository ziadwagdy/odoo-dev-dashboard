import base64
import inspect
import json
import logging

from odoo import http
from odoo.exceptions import AccessDenied
from odoo.http import request

_logger = logging.getLogger(__name__)


def _safe_redirect(target):
    # same-site relative paths only (no open redirect)
    if target and target.startswith('/') and not target.startswith('//') and '\\' not in target:
        return target
    return '/web'


class DashboardLogin(http.Controller):

    @http.route('/dashboard/login', type='http', auth='none', methods=['GET'], csrf=False)
    def dashboard_login(self, t='', db=None, redirect='/web', **kw):
        try:
            body = t.rpartition('.')[0]
            payload = json.loads(base64.urlsafe_b64decode(body + '=' * (-len(body) % 4)))
            login, token_db = payload['login'], payload['db']
        except Exception:
            return request.make_response('Invalid link', status=400)
        dbname = db or token_db
        if dbname != token_db:
            return request.make_response('Invalid link', status=400)
        params = inspect.signature(request.session.authenticate).parameters
        try:
            if 'credential' in params:      # Odoo 18+
                credential = {'type': 'dashboard_sso', 'login': login, 'token': t}
                first = next(iter(params))
                # Odoo 18: authenticate(dbname, credential); Odoo 19: authenticate(env, credential)
                request.session.authenticate(request.env if first == 'env' else dbname, credential)
            else:                           # Odoo 17
                request.session.authenticate(dbname, login, 'dashsso:' + t)
        except AccessDenied:
            _logger.warning('dashboard login refused for %s on %s', login, dbname)
            return request.make_response('This sign-in link is invalid or has expired.', status=403)
        _logger.info('dashboard login: %s on %s', login, dbname)
        return request.redirect(_safe_redirect(redirect))
