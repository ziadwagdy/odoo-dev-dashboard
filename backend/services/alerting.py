"""De-duplicate, escalate and announce security events.

One open alert per key inside a time window: repeated events increase its count instead of
creating noise; warnings escalate as the count grows; notifiers are told once when an alert is
new and again only when it escalates. A broken notifier never loses an alert.
"""
import datetime as dt
import logging

from django.utils import timezone

from apps.security.models import SecurityAlert

log = logging.getLogger(__name__)

RANK = {'info': 0, 'warning': 1, 'high': 2, 'critical': 3}
# a warning-level key seen this many times is promoted
ESCALATION = ((20, 'critical'), (5, 'high'))


class AlertManager:
    def __init__(self, notifiers=None, window=dt.timedelta(minutes=15), ignore=()):
        self.notifiers = notifiers if notifiers is not None else []
        self.window = window
        self.ignore = set(ignore)

    def _announce(self, alert, kind):
        for n in list(self.notifiers):
            try:
                n.notify(alert, kind)
            except Exception:                      # pragma: no cover - exercised in tests
                log.exception('notifier %r failed for alert %s', n, alert.id)

    def handle(self, event):
        if any(token in event.key for token in self.ignore):
            return None
        now = timezone.now()
        alert = (SecurityAlert.objects.filter(key=event.key, status='open', last_seen__gte=now - self.window)
                 .order_by('-last_seen').first())
        if alert is None:
            alert = SecurityAlert.objects.create(
                rule=event.rule, severity=event.severity, source=event.source, key=event.key,
                summary=event.summary[:300], sample=event.sample[:300], last_seen=now)
            self._announce(alert, 'new')
            return alert

        alert.count += 1
        alert.last_seen = now
        escalated = False
        if event.severity == 'warning':
            for threshold, level in ESCALATION:
                if alert.count >= threshold and RANK[level] > RANK[alert.severity]:
                    alert.severity, escalated = level, True
                    break
        alert.save()
        if escalated:
            self._announce(alert, 'escalated')
        return alert
