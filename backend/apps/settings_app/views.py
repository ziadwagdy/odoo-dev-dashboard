from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from core.permissions import IsAdmin

from services.registry import get_project
import time

from django.utils import timezone

from services import settings_schema
from services.docker_service import restart_container, exec_in_container_sync
from services.cron_scheduler import reschedule_job
from apps.projects.models import CronJob, AuditLog, UserProjectAssignment, ConfigChangeRequest
from apps.projects.serializers import CronJobSerializer


def _can_access(user, project):
    if user.groups.filter(name='admin').exists():
        return True
    return UserProjectAssignment.objects.filter(user=user, project_name=project).exists()


def _audit(project, action, detail='', outcome='success', user=''):
    try:
        AuditLog.objects.create(project=project, action=action, detail=detail, outcome=outcome, user=user)
    except Exception:
        pass


# ── Runtime settings: curated, validated, change-request based ───────────
#
# The whole odoo.conf is never shown or written from the dashboard. Users see
# (and may request changes to) a small allow-listed set of runtime settings; a
# change only reaches odoo.conf after an admin has reviewed the validated diff.

def _serialize(r):
    return {
        'id': r.id, 'project': r.project, 'status': r.status, 'requested_by': r.requested_by,
        'requested_at': r.requested_at.isoformat(), 'changes': r.changes, 'previous': r.previous,
        'warnings': r.warnings, 'reason': r.reason, 'restart_required': r.restart_required,
        'decided_by': r.decided_by, 'decided_at': r.decided_at.isoformat() if r.decided_at else None,
        'decision_note': r.decision_note, 'applied_at': r.applied_at.isoformat() if r.applied_at else None,
        'result': r.result,
    }


def _project_or_404(request, project):
    if not _can_access(request.user, project):
        return None, Response({'error': 'Access denied'}, status=403)
    p = get_project(project)
    if not p:
        return None, Response({'error': 'project not found'}, status=404)
    return p, None


@api_view(['GET'])
def runtime_settings(request, project):
    p, err = _project_or_404(request, project)
    if err:
        return err
    data = settings_schema.describe(p)
    data['pending'] = [_serialize(r) for r in ConfigChangeRequest.objects.filter(project=project, status='pending')]
    data['history'] = [_serialize(r) for r in ConfigChangeRequest.objects.filter(project=project).exclude(status='pending')[:15]]
    data['can_approve'] = request.user.groups.filter(name='admin').exists()
    return Response(data)


@api_view(['POST'])
def change_validate(request, project):
    """Dry run: returns what would change plus errors/warnings, stores nothing."""
    p, err = _project_or_404(request, project)
    if err:
        return err
    clean, errors, warnings = settings_schema.validate(p, request.data.get('changes'))
    cur = settings_schema.current_values(p)
    return Response({
        'ok': not errors, 'errors': errors, 'warnings': warnings,
        'diff': [{'key': k, 'label': settings_schema.SCHEMA[k]['label'], 'from': cur[k]['value'], 'to': v}
                 for k, v in clean.items()],
        'restart_required': settings_schema.restart_needed(clean) if clean else False,
    })


@api_view(['POST'])
def change_create(request, project):
    p, err = _project_or_404(request, project)
    if err:
        return err
    clean, errors, warnings = settings_schema.validate(p, request.data.get('changes'))
    if errors:
        return Response({'ok': False, 'errors': errors, 'warnings': warnings}, status=400)
    if ConfigChangeRequest.objects.filter(project=project, status='pending', requested_by=request.user.username).count() >= 5:
        return Response({'ok': False, 'errors': ['You already have 5 pending requests for this project.']}, status=400)
    cur = settings_schema.current_values(p)
    req = ConfigChangeRequest.objects.create(
        project=project, requested_by=request.user.username, changes=clean,
        previous={k: cur[k]['value'] for k in clean}, warnings=warnings,
        reason=str(request.data.get('reason', ''))[:1000],
        restart_required=settings_schema.restart_needed(clean))
    _audit(project, 'config_request', ', '.join(f'{k}={v}' for k, v in clean.items()), user=request.user.username)
    return Response({'ok': True, 'request': _serialize(req)}, status=201)


@api_view(['POST'])
def change_cancel(request, project, request_id):
    r = ConfigChangeRequest.objects.filter(id=request_id, project=project, status='pending').first()
    if not r:
        return Response({'error': 'pending request not found'}, status=404)
    if r.requested_by != request.user.username and not request.user.groups.filter(name='admin').exists():
        return Response({'error': 'Only the requester or an admin can cancel'}, status=403)
    r.status, r.decided_by, r.decided_at = 'cancelled', request.user.username, timezone.now()
    r.save()
    _audit(project, 'config_cancel', f'#{r.id}', user=request.user.username)
    return Response({'ok': True})


@api_view(['POST'])
@permission_classes([IsAdmin])
def change_reject(request, project, request_id):
    r = ConfigChangeRequest.objects.filter(id=request_id, project=project, status='pending').first()
    if not r:
        return Response({'error': 'pending request not found'}, status=404)
    r.status, r.decided_by, r.decided_at = 'rejected', request.user.username, timezone.now()
    r.decision_note = str(request.data.get('note', ''))[:1000]
    r.save()
    _audit(project, 'config_reject', f'#{r.id} by {r.requested_by}', user=request.user.username)
    return Response({'ok': True})


def _health_ok(container):
    code = ("import urllib.request,sys\n"
            "try:\n print(urllib.request.urlopen('http://127.0.0.1:8069/web/health', timeout=5).status)\n"
            "except Exception as e:\n print('ERR', e)\n")
    for _ in range(20):
        exit_code, out = exec_in_container_sync(container, ['python3', '-c', code])
        if exit_code == 0 and b'200' in (out if isinstance(out, bytes) else str(out).encode()):
            return True
        time.sleep(3)
    return False


@api_view(['POST'])
@permission_classes([IsAdmin])
def change_approve(request, project, request_id):
    """Re-validate against the *current* state, back up, write only the requested
    keys, restart when needed, health-check, and roll back automatically on failure."""
    p, err = _project_or_404(request, project)
    if err:
        return err
    r = ConfigChangeRequest.objects.filter(id=request_id, project=project, status='pending').first()
    if not r:
        return Response({'error': 'pending request not found'}, status=404)
    if request.data.get('confirm') is not True:
        return Response({'ok': False, 'errors': ['Explicit confirmation required (confirm: true).']}, status=400)

    cur = settings_schema.current_values(p)
    drifted = [k for k, v in r.previous.items() if cur[k]['value'] != v]
    if drifted:
        return Response({'ok': False, 'errors': [
            'These settings changed since the request was made: ' + ', '.join(drifted) +
            '. Reject this request and submit a new one.']}, status=409)
    clean, errors, warnings = settings_schema.validate(p, r.changes)
    if errors:
        return Response({'ok': False, 'errors': errors}, status=400)
    if warnings and request.data.get('accept_warnings') is not True:
        return Response({'ok': False, 'needs_warning_ack': True, 'warnings': warnings,
                         'errors': ['This change has warnings; acknowledge them to continue.']}, status=409)

    container = f"{p['name']}-app"
    backup = settings_schema.backup_conf(p)
    r.decided_by, r.decided_at, r.decision_note = request.user.username, timezone.now(), str(request.data.get('note', ''))[:1000]
    try:
        settings_schema.write_values(p, clean)
        restarted = False
        if settings_schema.restart_needed(clean) and request.data.get('restart', True):
            restart_container(container)
            restarted = True
            if not _health_ok(container):
                raise RuntimeError('the application did not become healthy after the restart')
        r.status, r.applied_at = 'applied', timezone.now()
        r.result = 'applied' + (' and restarted' if restarted else ' (restart pending)')
        r.save()
        _audit(project, 'config_apply', f'#{r.id}: ' + ', '.join(f'{k}={v}' for k, v in clean.items()),
               user=request.user.username)
        return Response({'ok': True, 'restarted': restarted, 'request': _serialize(r)})
    except Exception as e:
        try:
            settings_schema.restore_conf(p, backup)
            if settings_schema.restart_needed(clean):
                restart_container(container)
            rolled = 'previous configuration restored'
        except Exception as e2:  # pragma: no cover
            rolled = f'ROLLBACK FAILED: {e2}'
        r.status, r.result = 'failed', f'{e}; {rolled}'
        r.save()
        _audit(project, 'config_apply', f'#{r.id}', outcome='failed', user=request.user.username)
        return Response({'ok': False, 'errors': [f'{e}. {rolled}.']}, status=500)


@api_view(['GET'])
def cron_get(request, project):
    try:
        job = CronJob.objects.get(project=project)
        return Response(CronJobSerializer(job).data)
    except CronJob.DoesNotExist:
        return Response({
            'project': project,
            'schedule': '*/2 * * * *',
            'enabled': True,
            'last_run': None,
            'last_result': None,
        })


@api_view(['POST'])
@permission_classes([IsAdmin])
def cron_save(request, project):
    p = get_project(project)
    if not p:
        return Response({'error': 'project not found'}, status=404)
    job, _ = CronJob.objects.get_or_create(project=project)
    job.schedule = request.data.get('schedule', job.schedule)
    job.enabled = request.data.get('enabled', job.enabled)
    job.save()
    reschedule_job(job)
    _audit(project, 'cron_save', f'schedule={job.schedule} enabled={job.enabled}', user=request.user.username)
    return Response(CronJobSerializer(job).data)
