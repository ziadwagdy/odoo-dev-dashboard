import os
import queue
import threading
import time

from django.conf import settings
from django.http import FileResponse, HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response

from services.registry import read_registry, get_project
from services.docker_service import get_container_status, restart_container, stop_container, get_container_logs, get_docker_client
from services.git_service import get_git_info, get_commit_log, get_current_commit, get_addons_path, git_pull
from services.db_service import (list_databases, backup_database, duplicate_database, drop_database,
                                  list_modules_grouped, list_backup_files, restore_database)
from state import deploy_queues, get_deploy_lock
from .models import DeployHistory
from .serializers import DeployHistorySerializer


@api_view(['GET'])
def api_config(request):
    return Response({
        'logs_url': settings.LOGS_URL,
        'files_url': settings.FILES_URL,
        'terminal_url': settings.TERMINAL_URL,
        'dashboard_title': settings.DASHBOARD_TITLE,
    })


@api_view(['GET'])
def api_status(request):
    projects = read_registry()
    docker = get_docker_client()
    for p in projects:
        p['status'] = get_container_status(p['container'])
        p['running'] = p['status'] == 'running'
        try:
            p['container_id'] = docker.containers.get(p['container']).short_id
        except Exception:
            p['container_id'] = None
    return Response({'projects': projects})


@api_view(['POST'])
def api_restart(request, container_name):
    try:
        restart_container(container_name)
        return Response({'ok': True})
    except Exception as e:
        return Response({'ok': False, 'error': str(e)}, status=500)


@api_view(['POST'])
def api_stop(request, container_name):
    try:
        stop_container(container_name)
        return Response({'ok': True})
    except Exception as e:
        return Response({'ok': False, 'error': str(e)}, status=500)


@api_view(['GET'])
def logs_download(request, container_name):
    logs_bytes = b''.join(get_container_logs(container_name, tail=2000, follow=False))
    response = HttpResponse(logs_bytes, content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename={container_name}.log'
    return response


@api_view(['GET'])
def db_list(request, project):
    p = get_project(project)
    if not p:
        return Response({'error': 'project not found'}, status=404)
    result = list_databases(p['db_port'])
    if isinstance(result, dict) and 'error' in result:
        return Response(result, status=500)
    return Response({'databases': result})


@api_view(['POST'])
def db_backup(request, project, dbname):
    p = get_project(project)
    if not p:
        return Response({'error': 'project not found'}, status=404)
    backup_dir = os.path.join(settings.DATA_DIR, 'backups', project)
    try:
        _filepath, filename = backup_database(p['db_port'], dbname, backup_dir)
        return Response({'ok': True, 'filename': filename, 'download_url': f'/api/db/{project}/download/{filename}'})
    except Exception as e:
        return Response({'ok': False, 'error': str(e)}, status=500)


@api_view(['GET'])
def db_download(request, project, filename):
    filename = os.path.basename(filename)
    backup_dir = os.path.join(settings.DATA_DIR, 'backups', project)
    filepath = os.path.join(backup_dir, filename)
    if not os.path.exists(filepath):
        return Response({'error': 'file not found'}, status=404)
    return FileResponse(open(filepath, 'rb'), as_attachment=True, filename=filename)


@api_view(['POST'])
def db_duplicate(request, project, dbname):
    p = get_project(project)
    if not p:
        return Response({'error': 'project not found'}, status=404)
    new_name = (request.data.get('new_name') or '').strip()
    if not new_name:
        return Response({'error': 'new_name required'}, status=400)
    try:
        duplicate_database(p['db_port'], dbname, new_name)
        return Response({'ok': True})
    except Exception as e:
        return Response({'ok': False, 'error': str(e)}, status=500)


@api_view(['DELETE'])
def db_drop(request, project, dbname):
    p = get_project(project)
    if not p:
        return Response({'error': 'project not found'}, status=404)
    if request.data.get('confirm') != dbname:
        return Response({'error': 'send {"confirm": "<dbname>"} to confirm'}, status=400)
    try:
        drop_database(p['db_port'], dbname)
        return Response({'ok': True})
    except Exception as e:
        return Response({'ok': False, 'error': str(e)}, status=500)


@api_view(['GET'])
def db_backups_list(request, project):
    backup_dir = os.path.join(settings.DATA_DIR, 'backups', project)
    files = list_backup_files(project, backup_dir)
    return Response({'backups': files})


@api_view(['POST'])
def db_restore(request, project, dbname):
    p = get_project(project)
    if not p:
        return Response({'error': 'project not found'}, status=404)
    if 'file' not in request.FILES:
        # Check if restoring from existing backup filename
        filename = request.data.get('filename')
        if filename:
            backup_dir = os.path.join(settings.DATA_DIR, 'backups', project)
            filepath = os.path.join(backup_dir, os.path.basename(filename))
            if not os.path.exists(filepath):
                return Response({'error': 'backup file not found'}, status=404)
            try:
                restore_database(p['db_port'], dbname, filepath)
                return Response({'ok': True})
            except Exception as e:
                return Response({'ok': False, 'error': str(e)}, status=500)
        return Response({'error': 'file required'}, status=400)

    uploaded = request.FILES['file']
    backup_dir = os.path.join(settings.DATA_DIR, 'backups', project)
    os.makedirs(backup_dir, exist_ok=True)
    filepath = os.path.join(backup_dir, os.path.basename(uploaded.name))
    with open(filepath, 'wb') as f:
        for chunk in uploaded.chunks():
            f.write(chunk)
    try:
        restore_database(p['db_port'], dbname, filepath)
        return Response({'ok': True})
    except Exception as e:
        return Response({'ok': False, 'error': str(e)}, status=500)


@api_view(['GET'])
def modules_list(request, project, dbname):
    p = get_project(project)
    if not p:
        return Response({'error': 'project not found'}, status=404)
    result = list_modules_grouped(p['db_port'], dbname, p['name'], settings.ODOO_DEV_BASE)
    if isinstance(result, dict) and 'error' in result:
        return Response(result, status=500)
    return Response(result)


@api_view(['POST'])
def module_update(request, project, dbname, module_name):
    p = get_project(project)
    if not p:
        return Response({'error': 'project not found'}, status=404)
    return Response({'ok': True, 'stream_url': f'/stream/module-update/{project}/{dbname}/{module_name}'})


@api_view(['POST'])
def deploy_project(request, name):
    p = get_project(name)
    if not p or not p.get('folder'):
        return Response({'error': 'project not found or no folder configured'}, status=404)

    lock = get_deploy_lock(name)
    if not lock.acquire(blocking=False):
        return Response({'ok': False, 'error': 'Deploy already in progress'}, status=409)

    prev_commit = get_current_commit(p['folder'])
    q = queue.Queue()
    deploy_queues[name] = q
    started_at = time.time()

    def _run():
        try:
            git_pull(p['folder'], q)
        finally:
            new_commit = get_current_commit(p['folder'])
            duration = round(time.time() - started_at, 1)
            _save_history(name, prev_commit, new_commit, duration)
            lock.release()

    threading.Thread(target=_run, daemon=True).start()
    return Response({'ok': True})


def _save_history(project, prev_commit, new_commit, duration):
    try:
        DeployHistory.objects.create(
            project=project,
            trigger_type='manual',
            prev_commit=prev_commit,
            new_commit=new_commit,
            outcome='success',
            duration_seconds=duration,
        )
    except Exception:
        pass


@api_view(['GET'])
def deploy_history(request, name):
    records = DeployHistory.objects.filter(project=name)[:20]
    return Response(DeployHistorySerializer(records, many=True).data)


@api_view(['GET'])
def project_detail(request, name):
    p = get_project(name)
    if not p:
        return Response({'error': 'project not found'}, status=404)
    p['status'] = get_container_status(p['container'])
    p['running'] = p['status'] == 'running'
    p['branch'], pending = get_git_info(p.get('folder'))
    p['pending_count'] = len(pending)
    p['commits'] = get_commit_log(p.get('folder'), n=10)
    p['addons_paths'] = get_addons_path(p['name'])
    return Response(p)
