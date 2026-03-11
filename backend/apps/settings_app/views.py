from rest_framework.decorators import api_view
from rest_framework.response import Response

from services.registry import get_project
from services.config_service import read_odoo_conf, write_odoo_conf, read_env_file, write_env_file
from services.cron_scheduler import reschedule_job
from apps.projects.models import CronJob
from apps.projects.serializers import CronJobSerializer


@api_view(['GET'])
def odoo_conf_read(request, project):
    p = get_project(project)
    if not p:
        return Response({'error': 'project not found'}, status=404)
    data = read_odoo_conf(project)
    if isinstance(data, dict) and 'error' in data:
        return Response(data, status=404)
    return Response(data)


@api_view(['POST'])
def odoo_conf_write(request, project):
    p = get_project(project)
    if not p:
        return Response({'error': 'project not found'}, status=404)
    try:
        write_odoo_conf(project, request.data)
        return Response({'ok': True})
    except Exception as e:
        return Response({'ok': False, 'error': str(e)}, status=500)


@api_view(['GET'])
def env_read(request, project):
    p = get_project(project)
    if not p:
        return Response({'error': 'project not found'}, status=404)
    data = read_env_file(project)
    return Response(data)


@api_view(['POST'])
def env_write(request, project):
    p = get_project(project)
    if not p:
        return Response({'error': 'project not found'}, status=404)
    try:
        write_env_file(project, request.data)
        return Response({'ok': True})
    except Exception as e:
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
def cron_save(request, project):
    p = get_project(project)
    if not p:
        return Response({'error': 'project not found'}, status=404)
    job, _ = CronJob.objects.get_or_create(project=project)
    job.schedule = request.data.get('schedule', job.schedule)
    job.enabled = request.data.get('enabled', job.enabled)
    job.save()
    reschedule_job(job)
    return Response(CronJobSerializer(job).data)
