import base64
import hashlib
import hmac
import json

import pytest

from services import sso

from ..conftest import MASTER

PROJECT = {'name': 'alpha', 'conf_file': 'alpha/config/odoo.conf', 'url': 'alpha.example.org'}


def _decode(token):
    body, sig = token.rsplit('.', 1)
    return json.loads(base64.urlsafe_b64decode(body + '=' * (-len(body) % 4))), body, sig


def test_token_is_signed_with_a_key_derived_from_the_master_password(odoo_base):
    token = sso.make_token(PROJECT, 'db1', 'admin')
    payload, body, sig = _decode(token)
    key = hashlib.sha256(('dashboard-sso:' + MASTER).encode()).digest()
    assert hmac.compare_digest(sig, hmac.new(key, body.encode(), hashlib.sha256).hexdigest())
    assert payload['db'] == 'db1' and payload['login'] == 'admin'


def test_token_is_short_lived_and_unique(odoo_base):
    a, _, _ = _decode(sso.make_token(PROJECT, 'db1', 'admin'))
    b, _, _ = _decode(sso.make_token(PROJECT, 'db1', 'admin'))
    assert a['exp'] - a['iat'] == sso.LINK_TTL
    assert a['n'] != b['n']


def test_ttl_is_capped_at_two_minutes(odoo_base):
    payload, _, _ = _decode(sso.make_token(PROJECT, 'db1', 'admin', ttl=86400))
    assert payload['exp'] - payload['iat'] == 120


def test_refuses_to_sign_with_a_weak_master_password(odoo_base):
    path = odoo_base / 'alpha' / 'config' / 'odoo.conf'
    path.write_text(path.read_text().replace(MASTER, 'admin'))
    with pytest.raises(RuntimeError):
        sso.make_token(PROJECT, 'db1', 'admin')


def test_a_token_from_another_project_does_not_verify(odoo_base):
    other = {'name': 'beta', 'conf_file': 'beta/config/odoo.conf', 'url': 'b'}
    _, body, sig = _decode(sso.make_token(other, 'db1', 'admin'))
    key = hashlib.sha256(('dashboard-sso:' + MASTER).encode()).digest()
    assert not hmac.compare_digest(sig, hmac.new(key, body.encode(), hashlib.sha256).hexdigest())
