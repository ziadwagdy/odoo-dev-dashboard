"""One quiet daily summary of what is still open, so nothing sits unnoticed."""
from apps.security.models import SecurityAlert

ORDER = ('critical', 'high', 'warning', 'info')


def build_digest():
    qs = SecurityAlert.objects.filter(status='open')
    d = {'open': qs.count()}
    for sev in ORDER[:3]:
        d[sev] = qs.filter(severity=sev).count()
    return d


def send_daily_digest(send):
    d = build_digest()
    if not d['open']:
        return False
    worst = next((s for s in ORDER if SecurityAlert.objects.filter(status='open', severity=s).exists()), 'info')
    parts = [f'{d[s]} {s}' for s in ORDER[:3] if d[s]]
    send(f"{d['open']} open security alert(s)", ', '.join(parts) + '. Open the Security page to review.', worst)
    return True
