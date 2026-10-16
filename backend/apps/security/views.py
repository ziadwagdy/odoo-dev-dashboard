from django.db.models import Case, IntegerField, Value, When
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from core.permissions import IsAdmin
from apps.projects.models import AuditLog
from .models import SecurityAlert

_RANK = Case(When(severity='critical', then=Value(0)), When(severity='high', then=Value(1)),
             When(severity='warning', then=Value(2)), default=Value(3), output_field=IntegerField())


def _serialize(a):
    return {'id': a.id, 'rule': a.rule, 'severity': a.severity, 'source': a.source, 'summary': a.summary,
            'sample': a.sample, 'count': a.count, 'first_seen': a.first_seen.isoformat(),
            'last_seen': a.last_seen.isoformat(), 'status': a.status,
            'acknowledged_by': a.acknowledged_by, 'note': a.note}


@api_view(['GET'])
@permission_classes([IsAdmin])
def alerts(request):
    qs = SecurityAlert.objects.annotate(rank=_RANK).order_by('status', 'rank', '-last_seen')[:200]
    return Response({'alerts': [_serialize(a) for a in qs]})


@api_view(['GET'])
@permission_classes([IsAdmin])
def summary(request):
    open_alerts = SecurityAlert.objects.filter(status='open')
    sev = {s: open_alerts.filter(severity=s).count() for s in ('critical', 'high')}
    worst = next((s for s in ('critical', 'high', 'warning', 'info') if open_alerts.filter(severity=s).exists()), None)
    return Response({'open': open_alerts.count(), 'critical': sev['critical'], 'high': sev['high'], 'worst': worst})


@api_view(['POST'])
@permission_classes([IsAdmin])
def acknowledge(request, alert_id):
    alert = SecurityAlert.objects.filter(id=alert_id).first()
    if not alert:
        return Response({'error': 'alert not found'}, status=404)
    alert.status, alert.acknowledged_by, alert.acknowledged_at = 'acknowledged', request.user.username, timezone.now()
    alert.note = str(request.data.get('note', ''))[:1000]
    alert.save()
    AuditLog.objects.create(project='system', action='security_ack', user=request.user.username,
                            detail=f'#{alert.id} {alert.rule} on {alert.source}', meta={'note': alert.note})
    return Response({'ok': True})
