"""Exercise the addon's real token verifier without requiring an Odoo runtime."""
import ast
import base64
import hashlib
import hmac
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[2] / 'odoo-addons/dashboard_login/models/res_users.py'
tree = ast.parse(SOURCE.read_text())
tree.body = [node for node in tree.body if isinstance(node, (ast.Import, ast.Assign, ast.FunctionDef))]
addon = {'tools': SimpleNamespace(config={'admin_passwd': 'test-master-password-at-least-16'})}
exec(compile(tree, str(SOURCE), 'exec'), addon)


class TokenValidityTests(unittest.TestCase):
    NOW = 1_800_000_000

    def token(self, *, age=0, ttl=60, **changes):
        payload = {'db': 'sivas', 'login': 'admin', 'iat': self.NOW - age,
                   'exp': self.NOW - age + ttl, 'n': 'test-nonce'}
        payload.update(changes)
        body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        return body + '.' + hmac.new(addon['_sso_key'](), body.encode(), hashlib.sha256).hexdigest()

    def verify(self, token):
        with patch.object(addon['time'], 'time', return_value=self.NOW):
            return addon['_verify'](token, 'admin', 'sivas')

    def test_valid_through_advertised_lifetime(self):
        for age in (0, 6, 27, 59):
            with self.subTest(age=age):
                self.assertIsNotNone(self.verify(self.token(age=age)))

    def test_expired_is_denied(self):
        self.assertIsNone(self.verify(self.token(age=61)))

    def test_small_future_clock_skew_is_allowed(self):
        self.assertIsNotNone(self.verify(self.token(age=-4)))

    def test_future_issued_token_is_denied(self):
        self.assertIsNone(self.verify(self.token(age=-6)))

    def test_overlong_and_nonpositive_lifetimes_are_denied(self):
        for ttl in (121, 3600, 0, -1):
            with self.subTest(ttl=ttl):
                self.assertIsNone(self.verify(self.token(ttl=ttl)))

    def test_wrong_database_and_login_are_denied(self):
        self.assertIsNone(self.verify(self.token(db='other')))
        self.assertIsNone(self.verify(self.token(login='other')))

    def test_tampered_signature_is_denied(self):
        self.assertIsNone(self.verify(self.token()[:-4] + 'zzzz'))


if __name__ == '__main__':
    unittest.main()
