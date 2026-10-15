from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from core.permissions import IsAdmin

from services.registry import get_project
from services.config_service import read_odoo_conf, write_odoo_conf, read_env_file, write_env_file
from services.cron_scheduler import reschedule_job
from apps.projects.models import CronJob, AuditLog, UserProjectAssignment
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


@api_view(['GET'])
def odoo_conf_read(request, project):
    if not _can_access(request.user, project):
        return Response({'error': 'Access denied'}, status=403)
    p = get_project(project)
    if not p:
        return Response({'error': 'project not found'}, status=404)
    data = read_odoo_conf(project, p.get('folder'), p.get('conf_file'))
    if isinstance(data, dict) and 'error' in data:
        return Response(data, status=404)
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAdmin])
def odoo_conf_write(request, project):
    p = get_project(project)
    if not p:
        return Response({'error': 'project not found'}, status=404)
    try:
        write_odoo_conf(project, request.data, p.get('folder'), p.get('conf_file'))
        _audit(project, 'config_save', 'odoo.conf', user=request.user.username)
        return Response({'ok': True})
    except Exception as e:
        _audit(project, 'config_save', 'odoo.conf', outcome='failed', user=request.user.username)
        return Response({'ok': False, 'error': str(e)}, status=500)


@api_view(['GET'])
def env_read(request, project):
    if not _can_access(request.user, project):
        return Response({'error': 'Access denied'}, status=403)
    p = get_project(project)
    if not p:
        return Response({'error': 'project not found'}, status=404)
    data = read_env_file(project, p.get('folder'))
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAdmin])
def env_write(request, project):
    p = get_project(project)
    if not p:
        return Response({'error': 'project not found'}, status=404)
    try:
        write_env_file(project, request.data, p.get('folder'))
        _audit(project, 'config_save', '.env', user=request.user.username)
        return Response({'ok': True})
    except Exception as e:
        _audit(project, 'config_save', '.env', outcome='failed', user=request.user.username)
        return Response({'ok': False, 'error': str(e)}, status=500)


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
