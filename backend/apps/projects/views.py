import os
import queue
import re
import shutil
import subprocess
import threading
import time

from django.conf import settings
from django.http import FileResponse, HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from core.permissions import IsAdmin, IsAdminOrManager

from services.registry import read_registry, get_project
from services.health_service import get_all_project_storage
from services.docker_service import get_container_status, restart_container, start_container, stop_container, get_container_logs, get_docker_client
from services.git_service import get_git_info, get_commit_log, get_current_commit, get_addons_path, git_pull, switch_branch, get_branches_quick
from services.db_service import (list_databases, backup_database, duplicate_database, drop_database,
                                  list_modules_grouped, list_backup_files, restore_database, neutralize_database,
                                  set_odoo_user_password, create_odoo_database)
from services import sso as sso_service
from services.access_policy import can_open_as
from core.net import client_ip
from state import deploy_queues, get_deploy_lock
from .models import DeployHistory, BackupSchedule, AuditLog, UserProjectAssignment
from .serializers import DeployHistorySerializer, BackupScheduleSerializer, AuditLogSerializer


def _is_admin(user):
    return user.groups.filter(name='admin').exists()


def _can_access_project(user, project_name):
    if _is_admin(user):
        return True
    return UserProjectAssignment.objects.filter(user=user, project_name=project_name).exists()


def _filter_projects(user, projects):
    if _is_admin(user):
        return projects
    allowed = set(UserProjectAssignment.objects.filter(user=user).values_list('project_name', flat=True))
    return [p for p in projects if p['name'] in allowed]


def _audit(project, action, detail='', outcome='success', user='', ip='', meta=None):
    try:
        AuditLog.objects.create(project=project, action=action, detail=detail, outcome=outcome,
                                user=user, ip=ip, meta=meta or {})
    except Exception:
        pass


@api_view(['GET'])
def api_storage(request):
    import psutil
    projects = _filter_projects(request.user, read_registry())
    storage = get_all_project_storage(projects)
    disk = psutil.disk_usage('/')
    return Response({
        'projects': storage,
        'disk_used_gb':  round(disk.used  / 1024 ** 3, 1),
        'disk_total_gb': round(disk.total / 1024 ** 3, 1),
        'disk_pct':      round(disk.percent, 1),
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def api_config(request):
    return Response({
        'logs_url': settings.LOGS_URL,
        'files_url': settings.FILES_URL,
        'terminal_url': settings.TERMINAL_URL,
        'dashboard_title': settings.DASHBOARD_TITLE,
    })


@api_view(['GET'])
def api_status(request):
    all_projects = _filter_projects(request.user, read_registry())
    docker = get_docker_client()

    for p in all_projects:
        p['status'] = get_container_status(p['container'])
        p['running'] = p['status'] == 'running'
        try:
            p['container_id'] = docker.containers.get(p['container']).short_id
        except Exception:
            p['container_id'] = None
        p['branch'], pending = get_git_info(p.get('folder'))
        p['pending_count'] = len(pending)

    return Response({'projects': all_projects})


@api_view(['POST'])
def api_restart(request, container_name):
    project = container_name.removesuffix('-app')
    if not _can_access_project(request.user, project):
        return Response({'error': 'Access denied'}, status=403)
    try:
        restart_container(container_name)
        _audit(project, 'container_restart', container_name, user=request.user.username)
        return Response({'ok': True})
    except Exception as e:
        _audit(project, 'container_restart', container_name, outcome='failed', user=request.user.username)
        return Response({'ok': False, 'error': str(e)}, status=500)


@api_view(['POST'])
def api_stop(request, container_name):
    project = container_name.removesuffix('-app')
    if not _can_access_project(request.user, project):
        return Response({'error': 'Access denied'}, status=403)
    try:
        stop_container(container_name)
        _audit(project, 'container_stop', container_name, user=request.user.username)
        return Response({'ok': True})
    except Exception as e:
        _audit(project, 'container_stop', container_name, outcome='failed', user=request.user.username)
        return Response({'ok': False, 'error': str(e)}, status=500)


@api_view(['POST'])
def api_start(request, container_name):
    project = container_name.removesuffix('-app')
    if not _can_access_project(request.user, project):
        return Response({'error': 'Access denied'}, status=403)
    try:
        start_container(container_name)
        _audit(project, 'container_start', container_name, user=request.user.username)
        return Response({'ok': True})
    except Exception as e:
        _audit(project, 'container_start', container_name, outcome='failed', user=request.user.username)
        return Response({'ok': False, 'error': str(e)}, status=500)


@api_view(['GET'])
def logs_download(request, container_name):
    if not _can_access_project(request.user, container_name.removesuffix('-app')):
        return Response({'error': 'Access denied'}, status=403)
    logs_bytes = b''.join(get_container_logs(container_name, tail=2000, follow=False))
    response = HttpResponse(logs_bytes, content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename={container_name}.log'
    return response


@api_view(['GET'])
def db_list(request, project):
    if not _can_access_project(request.user, project):
        return Response({'error': 'Access denied'}, status=403)
    p = get_project(project)
    if not p:
        return Response({'error': 'project not found'}, status=404)
    result = list_databases(p['db_port'])
    if isinstance(result, dict) and 'error' in result:
        return Response(result, status=500)
    return Response({'databases': result})


@api_view(['POST'])
def db_backup(request, project, dbname):
    if not _can_access_project(request.user, project):
        return Response({'error': 'Access denied'}, status=403)
    p = get_project(project)
    if not p:
        return Response({'error': 'project not found'}, status=404)
    backup_dir = os.path.join(settings.DATA_DIR, 'backups', project)
    try:
        _filepath, filename = backup_database(p['db_port'], dbname, backup_dir)
        _audit(project, 'backup', dbname, user=request.user.username)
        return Response({'ok': True, 'filename': filename, 'download_url': f'/api/db/{project}/download/{filename}'})
    except Exception as e:
        _audit(project, 'backup', dbname, outcome='failed', user=request.user.username)
        return Response({'ok': False, 'error': str(e)}, status=500)


@api_view(['GET'])
def db_download(request, project, filename):
    if not _can_access_project(request.user, project):
        return Response({'error': 'Access denied'}, status=403)
    filename = os.path.basename(filename)
    backup_dir = os.path.join(settings.DATA_DIR, 'backups', project)
    filepath = os.path.join(backup_dir, filename)
    if not os.path.exists(filepath):
        return Response({'error': 'file not found'}, status=404)
    return FileResponse(open(filepath, 'rb'), as_attachment=True, filename=filename)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def db_duplicate(request, project, dbname):
    if not _can_access_project(request.user, project):
        return Response({'error': 'Access denied'}, status=403)
    p = get_project(project)
    if not p:
        return Response({'error': 'project not found'}, status=404)
    new_name = (request.data.get('new_name') or '').strip()
    if not new_name:
        return Response({'error': 'new_name required'}, status=400)
    try:
        duplicate_database(p['db_port'], dbname, new_name, project_name=p['name'])
        _audit(project, 'db_duplicate', f'{dbname} → {new_name} (neutralized)', user=request.user.username)
        return Response({'ok': True})
    except Exception as e:
        _audit(project, 'db_duplicate', f'{dbname} → {new_name}', outcome='failed', user=request.user.username)
        return Response({'ok': False, 'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def db_neutralize(request, project, dbname):
    if not _can_access_project(request.user, project):
        return Response({'error': 'Access denied'}, status=403)
    p = get_project(project)
    if not p:
        return Response({'error': 'project not found'}, status=404)
    try:
        neutralize_database(p['name'], dbname)
        _audit(project, 'db_neutralize', dbname, user=request.user.username)
        return Response({'ok': True})
    except Exception as e:
        _audit(project, 'db_neutralize', dbname, outcome='failed', user=request.user.username)
        return Response({'ok': False, 'error': str(e)}, status=500)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def db_drop(request, project, dbname):
    if not _can_access_project(request.user, project):
        return Response({'error': 'Access denied'}, status=403)
    p = get_project(project)
    if not p:
        return Response({'error': 'project not found'}, status=404)
    if request.data.get('confirm') != dbname:
        return Response({'error': 'send {"confirm": "<dbname>"} to confirm'}, status=400)
    try:
        drop_database(p['db_port'], dbname)
        _audit(project, 'db_drop', dbname, user=request.user.username)
        return Response({'ok': True})
    except Exception as e:
        _audit(project, 'db_drop', dbname, outcome='failed', user=request.user.username)
        return Response({'ok': False, 'error': str(e)}, status=500)


@api_view(['GET'])
def db_backups_list(request, project):
    if not _can_access_project(request.user, project):
        return Response({'error': 'Access denied'}, status=403)
    backup_dir = os.path.join(settings.DATA_DIR, 'backups', project)
    files = list_backup_files(project, backup_dir)
    return Response({'backups': files})


@api_view(['POST'])
def db_restore(request, project, dbname):  # developer-allowed
    if not _can_access_project(request.user, project):
        return Response({'error': 'Access denied'}, status=403)
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
                restore_database(p['db_port'], dbname, filepath, project_name=p['name'])
                _audit(project, 'restore', f'{filename} → {dbname} (neutralized)', user=request.user.username)
                return Response({'ok': True})
            except Exception as e:
                _audit(project, 'restore', f'{filename} → {dbname}', outcome='failed', user=request.user.username)
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
        restore_database(p['db_port'], dbname, filepath, project_name=p['name'])
        _audit(project, 'restore', f'{uploaded.name} → {dbname} (neutralized)', user=request.user.username)
        return Response({'ok': True})
    except Exception as e:
        _audit(project, 'restore', f'{uploaded.name} → {dbname}', outcome='failed', user=request.user.username)
        return Response({'ok': False, 'error': str(e)}, status=500)


@api_view(['GET'])
def modules_list(request, project, dbname):
    if not _can_access_project(request.user, project):
        return Response({'error': 'Access denied'}, status=403)
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
    if not _can_access_project(request.user, project):
        return Response({'error': 'Access denied'}, status=403)
    p = get_project(project)
    if not p:
        return Response({'error': 'project not found'}, status=404)
    return Response({'ok': True, 'stream_url': f'/stream/module-update/{project}/{dbname}/{module_name}'})


@api_view(['POST'])
@permission_classes([IsAdmin])
def deploy_project(request, name):
    if not _can_access_project(request.user, name):
        return Response({'error': 'Access denied'}, status=403)
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
            _audit(name, 'deploy', f'{(prev_commit or "")[:7]} → {(new_commit or "")[:7]}', outcome=outcome, user=request.user.username)
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
    if not _can_access_project(request.user, project):
        return Response({'error': 'Access denied'}, status=403)
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
@permission_classes([IsAuthenticated])
def backup_schedule_save(request, project, dbname):
    if not _can_access_project(request.user, project):
        return Response({'error': 'Access denied'}, status=403)
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
    _audit(project, 'backup_schedule', f'{dbname}: {sched.schedule}, enabled={sched.enabled}', user=request.user.username)
    return Response(BackupScheduleSerializer(sched).data)


@api_view(['GET'])
def audit_log(request, name):
    if not _can_access_project(request.user, name):
        return Response({'error': 'Access denied'}, status=403)
    records = AuditLog.objects.filter(project=name)[:50]
    return Response(AuditLogSerializer(records, many=True).data)


@api_view(['GET'])
def deploy_history(request, name):
    if not _can_access_project(request.user, name):
        return Response({'error': 'Access denied'}, status=403)
    records = DeployHistory.objects.filter(project=name)[:20]
    return Response(DeployHistorySerializer(records, many=True).data)


@api_view(['GET'])
def project_detail(request, name):
    if not _can_access_project(request.user, name):
        return Response({'error': 'Access denied'}, status=403)
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


@api_view(['DELETE'])
@permission_classes([IsAdmin])
def delete_project(request, name):
    p = get_project(name)
    if not p:
        return Response({'error': 'project not found'}, status=404)

    base = settings.ODOO_DEV_BASE
    folder = p.get('folder')  # e.g. 'projects/medtech' or 'projects/pac/repo'
    subdomain = p.get('url', '').replace('https://', '').replace('http://', '').rstrip('/')

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

    # Remove from Dozzle filter and restart Dozzle
    dozzle_compose = os.path.join(base, 'dozzle', 'docker-compose.yml')
    container_name = f'{name}-app'
    if os.path.exists(dozzle_compose):
        try:
            with open(dozzle_compose) as f:
                content = f.read()
            updated = re.sub(rf'\|{re.escape(container_name)}|{re.escape(container_name)}\|', '', content)
            if updated != content:
                with open(dozzle_compose, 'w') as f:
                    f.write(updated)
                subprocess.run(
                    ['docker', 'compose', 'up', '-d'],
                    cwd=os.path.dirname(dozzle_compose),
                    capture_output=True, timeout=30,
                )
        except Exception:
            pass  # Dozzle cleanup failure is non-fatal

    # Build manual cleanup commands for Nginx and Cloudflare (require sudo)
    manual_commands = [
        f'sudo rm /etc/nginx/conf.d/{name}.conf && sudo nginx -t && sudo systemctl reload nginx',
    ]
    if subdomain:
        manual_commands += [
            f"sudo sed -i '/  - hostname: {subdomain}/{{N;d}}' /etc/cloudflared/config.yml",
            'sudo systemctl restart cloudflared',
        ]

    _audit(name, 'project_delete', '', user=request.user.username)
    return Response({'ok': True, 'manual_commands': manual_commands})


def _is_admin_or_manager(user):
    return user.groups.filter(name__in=['admin', 'manager']).exists()


def _no_store(response):
    response['Cache-Control'] = 'no-store'
    return response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def db_create(request, project):
    """Create a new, empty Odoo database. The admin password is generated and
    returned once to the logged-in user; no master password is involved."""
    if not _can_access_project(request.user, project):
        return Response({'error': 'Access denied'}, status=403)
    p = get_project(project)
    if not p:
        return Response({'error': 'project not found'}, status=404)
    name = str(request.data.get('name', '')).strip()
    demo = bool(request.data.get('demo', False))
    try:
        login_name, password = create_odoo_database(p['name'], p['db_port'], name, demo=demo)
    except ValueError as e:
        return Response({'ok': False, 'error': str(e)}, status=400)
    except Exception as e:
        _audit(project, 'db_create', name, outcome='failed', user=request.user.username)
        return Response({'ok': False, 'error': str(e)}, status=500)
    _audit(project, 'db_create', f'{name} (demo={demo})', user=request.user.username)
    return _no_store(Response({'ok': True, 'name': name, 'login': login_name, 'password': password}))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def db_admin_password(request, project, dbname):
    """Issue an individual, random, shown-once Odoo login for this database
    (replaces sharing a fixed admin password). Admin/manager only, audited."""
    if not _can_access_project(request.user, project):
        return Response({'error': 'Access denied'}, status=403)
    if not _is_admin_or_manager(request.user):
        return Response({'error': 'Manager or admin privileges required.'}, status=403)
    p = get_project(project)
    if not p:
        return Response({'error': 'project not found'}, status=404)
    login_name = str(request.data.get('login', 'admin')).strip() or 'admin'
    try:
        password = set_odoo_user_password(p['name'], p['db_port'], dbname, login_name)
    except (ValueError, LookupError) as e:
        return Response({'ok': False, 'error': str(e)}, status=400)
    except Exception as e:
        _audit(project, 'db_admin_password', f'{dbname}/{login_name}', outcome='failed', user=request.user.username)
        return Response({'ok': False, 'error': str(e)}, status=500)
    _audit(project, 'db_admin_password', f'{dbname}/{login_name}', user=request.user.username)
    return _no_store(Response({'ok': True, 'login': login_name, 'password': password}))


def _role(user):
    for name in ('admin', 'manager', 'developer'):
        if user.groups.filter(name=name).exists():
            return name
    return None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def db_login_users(request, project, dbname):
    """Users of an Odoo database, annotated with what the caller's role may do with each."""
    if not _can_access_project(request.user, project):
        return Response({'error': 'Access denied'}, status=403)
    p = get_project(project)
    if not p:
        return Response({'error': 'project not found'}, status=404)
    try:
        users = sso_service.list_login_candidates(p['db_port'], dbname)
        neutralized = sso_service.database_state(p['db_port'], dbname)['neutralized']
    except ValueError as e:
        return Response({'error': str(e)}, status=400)
    except Exception as e:
        return Response({'error': str(e)}, status=500)
    role = _role(request.user)
    annotated = []
    for u in users:
        d = can_open_as(role, target_is_admin=u['admin'], db_neutralized=neutralized)
        annotated.append({**u, 'allowed': d.allowed, 'reason_required': d.reason_required, 'why': d.message})
    return Response({'users': annotated, 'neutralized': neutralized, 'role': role})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def db_login_link(request, project, dbname):
    """Return a 60-second, one-time link that signs the dashboard user into the chosen Odoo
    database as the chosen user. Role-gated, reason required where policy says so, audited."""
    if not _can_access_project(request.user, project):
        return Response({'error': 'Access denied'}, status=403)
    p = get_project(project)
    if not p:
        return Response({'error': 'project not found'}, status=404)
    login_name = str(request.data.get('login', 'admin')).strip() or 'admin'
    reason = str(request.data.get('reason', '')).strip()
    ip = client_ip(request)
    try:
        users = {u['login']: u for u in sso_service.list_login_candidates(p['db_port'], dbname)}
        neutralized = sso_service.database_state(p['db_port'], dbname)['neutralized']
    except ValueError as e:
        return Response({'ok': False, 'error': str(e)}, status=400)
    except Exception as e:
        return Response({'ok': False, 'error': str(e)}, status=500)
    target = users.get(login_name)
    if target is None:
        return Response({'ok': False, 'error': f'no active internal user {login_name!r} in {dbname}'}, status=400)

    decision = can_open_as(_role(request.user), target_is_admin=target['admin'],
                           db_neutralized=neutralized, reason=reason)
    meta = {'db': dbname, 'target': login_name, 'target_is_admin': target['admin'],
            'neutralized': neutralized, 'reason': reason, 'expires_in': sso_service.LINK_TTL}
    if not decision.allowed:
        _audit(project, 'db_login_link', f'{dbname} as {login_name}', outcome='denied',
               user=request.user.username, ip=ip, meta=meta)
        return Response({'ok': False, 'error': decision.message or 'Not allowed'}, status=403)
    if not decision.satisfied:
        return Response({'ok': False, 'reason_required': True,
                         'error': 'A reason is required for this sign-in (at least 8 characters).'}, status=400)
    try:
        url = sso_service.build_login_url(p, p['db_port'], dbname, login_name)
    except (ValueError, LookupError) as e:
        return Response({'ok': False, 'error': str(e)}, status=400)
    except Exception as e:
        _audit(project, 'db_login_link', f'{dbname} as {login_name}', outcome='failed',
               user=request.user.username, ip=ip, meta=meta)
        return Response({'ok': False, 'error': str(e)}, status=500)
    _audit(project, 'db_login_link', f'{dbname} as {login_name}', user=request.user.username, ip=ip, meta=meta)
    return _no_store(Response({'ok': True, 'url': url, 'expires_in': sso_service.LINK_TTL}))
