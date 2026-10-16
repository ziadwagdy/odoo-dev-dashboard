"""Web Push (VAPID) delivery of security alerts to admins' browsers and phones.

No third-party account is needed: the browser's own push service relays the message.
Payloads are short and never contain evidence lines, payloads or secrets.
"""
import base64
import json
import logging
import os

from django.conf import settings
from django.utils import timezone

from apps.security.models import PushSubscription

log = logging.getLogger(__name__)
VAPID_SUBJECT = os.environ.get('VAPID_SUBJECT', 'mailto:alerts@zedev.org')


# ── keys ───────────────────────────────────────────────────────────────────
def vapid_private_key_path():
    """Create the VAPID key pair once; the private key is readable by this process only."""
    path = os.path.join(settings.DATA_DIR, 'vapid_private.pem')
    if not os.path.exists(path):
        from py_vapid import Vapid
        os.makedirs(settings.DATA_DIR, exist_ok=True)
        vapid = Vapid()
        vapid.generate_keys()
        vapid.save_key(path)
        os.chmod(path, 0o600)
    return path


def public_key():
    """Application server key for the browser: url-safe base64 of the uncompressed point."""
    from cryptography.hazmat.primitives import serialization
    from py_vapid import Vapid
    vapid = Vapid.from_file(vapid_private_key_path())
    raw = vapid.public_key.public_bytes(serialization.Encoding.X962,
                                        serialization.PublicFormat.UncompressedPoint)
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode()


# ── delivery ───────────────────────────────────────────────────────────────
def _send(subscription_info, data=None, vapid_private_key=None, vapid_claims=None):
    from pywebpush import webpush
    webpush(subscription_info=subscription_info, data=data, vapid_private_key=vapid_private_key,
            vapid_claims=vapid_claims, ttl=3600, timeout=10)


def is_gone(exc):
    """The push service says this subscription no longer exists."""
    return getattr(getattr(exc, 'response', None), 'status_code', 0) in (404, 410)


def _deliver(sub, payload):
    try:
        _send({'endpoint': sub.endpoint, 'keys': {'p256dh': sub.p256dh, 'auth': sub.auth}},
              data=json.dumps(payload), vapid_private_key=vapid_private_key_path(),
              vapid_claims={'sub': VAPID_SUBJECT})
        PushSubscription.objects.filter(pk=sub.pk).update(last_ok=timezone.now())
        return True
    except Exception as exc:
        if is_gone(exc):
            sub.delete()
        else:
            log.warning('web push to %s failed: %s', sub.endpoint[:60], exc)
        return False


def send_to_user(user, title, body, severity='info', url='/security'):
    payload = {'title': title, 'body': body, 'severity': severity, 'url': url, 'tag': f'user-{user.id}-test'}
    return sum(1 for sub in PushSubscription.objects.filter(user=user) if _deliver(sub, payload))


class WebPushNotifier:
    """Pushes high/critical alerts (new) and any escalation; plain new warnings stay in the dashboard."""

    def notify(self, alert, kind):
        if not (alert.severity in ('high', 'critical') or kind == 'escalated'):
            return
        payload = {
            'title': f'{alert.severity.upper()}: {alert.summary}'[:120],
            'body': f'{alert.count} event(s) · {alert.source}',
            'severity': alert.severity, 'url': '/security', 'tag': f'alert-{alert.id}',
        }
        for sub in PushSubscription.objects.filter(user__groups__name='admin').distinct():
            _deliver(sub, payload)
