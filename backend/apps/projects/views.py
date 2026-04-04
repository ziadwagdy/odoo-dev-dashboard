import os
import queue
import shutil
import subprocess
import threading
import time

from django.conf import settings
from django.http import FileResponse, HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response

from services.registry import read_registry, get_project
from services.docker_service import get_container_status, restart_container, stop_container, get_container_logs, get_docker_client
from services.git_service import get_git_info, get_commit_log, get_current_commit, get_addons_path, git_pull, switch_branch, get_branches_quick
from services.db_service import (list_databases, backup_database, duplicate_database, drop_database,
                                  list_modules_grouped, list_backup_files, restore_database)
from state import deploy_queues, get_deploy_lock
from .models import DeployHistory, BackupSchedule, AuditLog, ProjectEnvironment, ProjectGroup
from .serializers import DeployHistorySerializer, BackupScheduleSerializer, AuditLogSerializer, ProjectEnvironmentSerializer, ProjectGroupSerializer


def _audit(project, action, detail='', outcome='success'):
    try:
        AuditLog.objects.create(project=project, action=action, detail=detail, outcome=outcome)
    except Exception:
        pass


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
    all_projects = read_registry()
    docker = get_docker_client()

    # Bulk-fetch environment configs to avoid N+1 queries
    envs = {e.project: e for e in ProjectEnvironment.objects.filter(
        project__in=[p['name'] for p in all_projects]
    )}

    for p in all_projects:
        p['status'] = get_container_status(p['container'])
        p['running'] = p['status'] == 'running'
        try:
            p['container_id'] = docker.containers.get(p['container']).short_id
        except Exception:
            p['container_id'] = None
        p['branch'], pending = get_git_info(p.get('folder'))
        p['pending_count'] = len(pending)
        env = envs.get(p['name'])
        p['environments'] = {
            'production': {'branch': env.production_branch if env else '', 'db': env.production_db if env else ''},
            'staging':    {'branch': env.staging_branch    if env else '', 'db': env.staging_db    if env else ''},
            'dev':        {'branch': env.dev_branch        if env else '', 'db': env.dev_db        if env else ''},
        }

    project_map = {p['name']: p for p in all_projects}

    # Build groups
    groups_qs = ProjectGroup.objects.all()
    groups_data = []
    grouped_instance_names = set()

    for g in groups_qs:
        instances = {}
        for env_type in ('production', 'staging', 'dev'):
            inst_name = getattr(g, f'{env_type}_instance')
            if inst_name and inst_name in project_map:
                instances[env_type] = project_map[inst_name]
                grouped_instance_names.add(inst_name)
            else:
                instances[env_type] = None
        groups_data.append({'name': g.name, 'instances': instances})

    ungrouped = [p for p in all_projects if p['name'] not in grouped_instance_names]

    return Response({'groups': groups_data, 'projects': ungrouped})


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
        _audit(project, 'backup', dbname)
        return Response({'ok': True, 'filename': filename, 'download_url': f'/api/db/{project}/download/{filename}'})
    except Exception as e:
        _audit(project, 'backup', dbname, outcome='failed')
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
        _audit(project, 'db_duplicate', f'{dbname} → {new_name}')
        return Response({'ok': True})
    except Exception as e:
        _audit(project, 'db_duplicate', f'{dbname} → {new_name}', outcome='failed')
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
        _audit(project, 'db_drop', dbname)
        return Response({'ok': True})
    except Exception as e:
        _audit(project, 'db_drop', dbname, outcome='failed')
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
                _audit(project, 'restore', f'{filename} → {dbname}')
                return Response({'ok': True})
            except Exception as e:
                _audit(project, 'restore', f'{filename} → {dbname}', outcome='failed')
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
        _audit(project, 'restore', f'{uploaded.name} → {dbname}')
        return Response({'ok': True})
    except Exception as e:
        _audit(project, 'restore', f'{uploaded.name} → {dbname}', outcome='failed')
        return Response({'ok': False, 'error': str(e)}, status=500)


@api_view(['GET'])
def modules_list(request, project, dbname):
    p = get_project(project)
    if not p:
        return Response({'error': 'project not found'}, status=404)
    result = list_modules_grouped(p['db_port'], dbname, p['name'], settings.ODOO_DEV_BASE,
                                   folder=p.get('folder'), version=p.get('version'))
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
        outcome = 'success'
        try:
            git_pull(p['folder'], q)
        except Exception:
            outcome = 'failed'
        finally:
            new_commit = get_current_commit(p['folder'])
            duration = round(time.time() - started_at, 1)
            _save_history(name, prev_commit, new_commit, duration)
            _audit(name, 'deploy', f'{(prev_commit or "")[:7]} → {(new_commit or "")[:7]}', outcome=outcome)
            lock.release()

    threading.Thread(target=_run, daemon=True).start()
    return Response({'ok': True})


@api_view(['POST'])
def record_deploy(request, name):
    """Lightweight endpoint for external tools (e.g. auto-deploy.sh) to record a deploy
    in history without triggering a git pull."""
    p = get_project(name)
    if not p:
        return Response({'error': 'project not found'}, status=404)
    commit = get_current_commit(p.get('folder'))
    trigger = request.data.get('trigger', 'auto')
    _save_history(name, commit, commit, 0, trigger_type=trigger)
    return Response({'ok': True})


def _save_history(project, prev_commit, new_commit, duration, trigger_type='manual'):
    try:
        DeployHistory.objects.create(
            project=project,
            trigger_type=trigger_type,
            prev_commit=prev_commit,
            new_commit=new_commit,
            outcome='success',
            duration_seconds=duration,
        )
    except Exception:
        pass


@api_view(['GET'])
def backup_schedule_get(request, project, dbname):
    try:
        sched = BackupSchedule.objects.get(project=project, dbname=dbname)
        return Response(BackupScheduleSerializer(sched).data)
    except BackupSchedule.DoesNotExist:
        return Response({
            'project': project, 'dbname': dbname,
            'schedule': '0 2 * * *', 'enabled': False,
            'retention': 7, 'last_run': None, 'last_result': None,
        })


@api_view(['POST'])
def backup_schedule_save(request, project, dbname):
    p = get_project(project)
    if not p:
        return Response({'error': 'project not found'}, status=404)
    from services.cron_scheduler import reschedule_backup_job
    sched, _ = BackupSchedule.objects.get_or_create(project=project, dbname=dbname)
    sched.schedule = request.data.get('schedule', sched.schedule)
    sched.enabled = request.data.get('enabled', sched.enabled)
    sched.retention = request.data.get('retention', sched.retention)
    sched.save()
    reschedule_backup_job(sched)
    return Response(BackupScheduleSerializer(sched).data)


@api_view(['GET'])
def audit_log(request, name):
    records = AuditLog.objects.filter(project=name)[:50]
    return Response(AuditLogSerializer(records, many=True).data)


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
    try:
        p['container_id'] = get_docker_client().containers.get(p['container']).short_id
    except Exception:
        p['container_id'] = None
    p['branch'], pending = get_git_info(p.get('folder'))
    p['pending_count'] = len(pending)
    p['commits'] = get_commit_log(p.get('folder'), n=10)
    p['addons_paths'] = get_addons_path(p['name'], p.get('folder'), version=p.get('version'))
    return Response(p)


@api_view(['GET', 'POST'])
def project_environments(request, name):
    p = get_project(name)
    if not p:
        return Response({'error': 'project not found'}, status=404)

    if request.method == 'POST':
        env, _ = ProjectEnvironment.objects.get_or_create(project=name)
        for field in ('production_branch', 'production_db',
                      'staging_branch',    'staging_db',
                      'dev_branch',        'dev_db'):
            if field in request.data:
                setattr(env, field, request.data[field])
        env.save()
        _audit(name, 'env_config',
               f'prod={env.production_branch}/{env.production_db} '
               f'staging={env.staging_branch}/{env.staging_db} '
               f'dev={env.dev_branch}/{env.dev_db}')
        return Response(ProjectEnvironmentSerializer(env).data)

    # GET: return current config + available branches + databases
    try:
        env = ProjectEnvironment.objects.get(project=name)
        data = ProjectEnvironmentSerializer(env).data
    except ProjectEnvironment.DoesNotExist:
        data = {
            'project': name,
            'production_branch': '', 'production_db': '',
            'staging_branch':    '', 'staging_db':    '',
            'dev_branch':        '', 'dev_db':        '',
        }

    data['branches']  = get_branches_quick(p['folder']) if p.get('folder') else []
    dbs = list_databases(p['db_port'])
    data['databases'] = dbs if isinstance(dbs, list) else []
    return Response(data)


@api_view(['POST'])
def deploy_environment(request, name, env_type):
    if env_type not in ('production', 'staging', 'dev'):
        return Response({'error': 'invalid env_type'}, status=400)

    p = get_project(name)
    if not p or not p.get('folder'):
        return Response({'error': 'project not found or no folder'}, status=404)

    try:
        env = ProjectEnvironment.objects.get(project=name)
    except ProjectEnvironment.DoesNotExist:
        return Response({'error': 'no environments configured'}, status=404)

    branch = env.branch_for(env_type)
    if not branch:
        return Response({'error': f'no branch configured for {env_type}'}, status=400)

    lock = get_deploy_lock(name)
    if not lock.acquire(blocking=False):
        return Response({'ok': False, 'error': 'Deploy already in progress'}, status=409)

    prev_commit = get_current_commit(p['folder'])
    q = queue.Queue()
    deploy_queues[name] = q
    started_at = time.time()

    def _run():
        outcome = 'success'
        try:
            q.put(f'[{env_type}] Switching to branch: {branch}')
            br_q = queue.Queue()
            switch_branch(p['folder'], branch, br_q)
            while True:
                msg = br_q.get()
                if msg is None:
                    break
                q.put(msg)
            q.put(f'[{env_type}] Pulling {branch}...')
            git_pull(p['folder'], q)
        except Exception as e:
            outcome = 'failed'
            q.put(f'Error: {e}')
            q.put(None)
        finally:
            new_commit = get_current_commit(p['folder'])
            duration = round(time.time() - started_at, 1)
            _save_history(name, prev_commit, new_commit, duration, trigger_type=f'{env_type}-deploy')
            _audit(name, 'deploy', f'{env_type}: {branch} → {(new_commit or "")[:7]}', outcome=outcome)
            lock.release()

    threading.Thread(target=_run, daemon=True).start()
    return Response({'ok': True, 'branch': branch, 'stream_url': f'/stream/deploy/{name}'})


@api_view(['GET'])
def list_groups(request):
    groups = ProjectGroup.objects.all()
    return Response(ProjectGroupSerializer(groups, many=True).data)


@api_view(['POST'])
def save_group(request):
    name = (request.data.get('name') or '').strip()
    if not name:
        return Response({'error': 'name required'}, status=400)
    group, _ = ProjectGroup.objects.get_or_create(name=name)
    for field in ('production_instance', 'staging_instance', 'dev_instance'):
        if field in request.data:
            setattr(group, field, request.data[field])
    group.save()
    return Response(ProjectGroupSerializer(group).data)


@api_view(['DELETE'])
def delete_group(request, group_name):
    try:
        ProjectGroup.objects.get(name=group_name).delete()
        return Response({'ok': True})
    except ProjectGroup.DoesNotExist:
        return Response({'error': 'not found'}, status=404)


@api_view(['DELETE'])
def delete_project(request, name):
    p = get_project(name)
    if not p:
        return Response({'error': 'project not found'}, status=404)

    base = settings.ODOO_DEV_BASE
    folder = p.get('folder')  # e.g. 'projects/medtech' or 'projects/pac/repo'

    # Find the docker-compose directory: start at folder, walk up until we find docker-compose.yml
    compose_dir = None
    if folder:
        candidate = os.path.join(base, folder)
        while candidate and candidate != base:
            if os.path.exists(os.path.join(candidate, 'docker-compose.yml')):
                compose_dir = candidate
                break
            candidate = os.path.dirname(candidate)

    # Stop containers and remove volumes
    if compose_dir and os.path.isdir(compose_dir):
        try:
            subprocess.run(
                ['docker', 'compose', 'down', '-v'],
                cwd=compose_dir, capture_output=True, timeout=60,
            )
        except Exception as e:
            return Response({'error': f'docker compose down failed: {e}'}, status=500)

        # Delete the project directory
        try:
            shutil.rmtree(compose_dir)
        except Exception as e:
            return Response({'error': f'Failed to remove directory: {e}'}, status=500)

    # Remove from registry
    registry_file = settings.REGISTRY_FILE
    try:
        with open(registry_file) as f:
            lines = f.readlines()
        with open(registry_file, 'w') as f:
            for line in lines:
                if not line.startswith(f'{name}|'):
                    f.write(line)
    except Exception as e:
        return Response({'error': f'Failed to update registry: {e}'}, status=500)

    return Response({'ok': True})
