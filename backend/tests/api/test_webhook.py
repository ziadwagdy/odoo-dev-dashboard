import hashlib
import hmac
import json


def test_webhook_fails_closed_when_no_secret_is_configured(anon, monkeypatch):
    monkeypatch.delenv('GITHUB_WEBHOOK_SECRET', raising=False)
    r = anon.post('/api/git/webhook/github', data=json.dumps({'ref': 'refs/heads/main'}), content_type='application/json')
    assert r.status_code in (401, 403)


def test_webhook_rejects_a_bad_signature(anon, monkeypatch):
    monkeypatch.setenv('GITHUB_WEBHOOK_SECRET', 's3cret')
    r = anon.post('/api/git/webhook/github', data='{}', content_type='application/json',
                  HTTP_X_HUB_SIGNATURE_256='sha256=' + '0' * 64)
    assert r.status_code in (401, 403)


def test_webhook_accepts_a_valid_signature(anon, monkeypatch):
    monkeypatch.setenv('GITHUB_WEBHOOK_SECRET', 's3cret')
    body = b'{"zen": "ping"}'
    sig = 'sha256=' + hmac.new(b's3cret', body, hashlib.sha256).hexdigest()
    r = anon.post('/api/git/webhook/github', data=body, content_type='application/json', HTTP_X_HUB_SIGNATURE_256=sig)
    assert r.status_code not in (401, 403)
