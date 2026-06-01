import asyncio
import json
import queue as queue_module
import threading

from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes

from core.permissions import IsAdmin, IsAdminOrManager

from services import onboard_service
from state import onboard_queues
from apps.projects.models import AuditLog


def _sse(data: dict) -> str:
    return f'data: {json.dumps(data)}\n\n'


def _sse_response(async_gen):
    response = StreamingHttpResponse(async_gen, content_type='text/event-stream')
    response['X-Accel-Buffering'] = 'no'
    response['Cache-Control'] = 'no-cache'
    response['Connection'] = 'keep-alive'
    return response


# ── Validation ───────────────────────────────────────────────────────

@api_view(['POST'])
def validate_project(request):
    data = request.data

    project_name = data.get('project_name', '').strip()
    subdomain    = data.get('subdomain', '').strip()
    version      = data.get('version')

    errors = {}

    valid, error = onboard_service.validate_project_name(project_name)
    if not valid:
        errors['project_name'] = error
    elif onboard_service.check_project_exists(project_name):
        errors['project_name'] = f"Project '{project_name}' already exists"

    valid, error = onboard_service.validate_subdomain(subdomain)
    if not valid:
        errors['subdomain'] = error

    if version and not onboard_service.check_worktrees_exist(version):
        errors['version'] = f'Worktrees for Odoo {version} not found'

    try:
        odoo_port, db_port = onboard_service.get_next_ports()
    except Exception as e:
        return JsonResponse({'valid': False, 'errors': {'general': str(e)}}, status=500)

    if errors:
        return JsonResponse({'valid': False, 'errors': errors}, status=400)

    return JsonResponse({
        'valid': True,
        'assigned_ports': {'odoo_port': odoo_port, 'db_port': db_port},
    })


# ── Start onboard ────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAdminOrManager])
def start_onboard(request):
    data = request.data

    project_name = data.get('project_name')
    repo_url     = data.get('repo_url')
    version      = data.get('version')
    subdomain    = data.get('subdomain')
    hr_base_mode = data.get('hr_base_mode', 'no')
    odoo_port    = data.get('odoo_port')
    db_port      = data.get('db_port')

    if not all([project_name, version, subdomain]):
        return JsonResponse({'success': False, 'error': 'Missing required fields'}, status=400)

    if project_name in onboard_queues:
        return JsonResponse({'success': False, 'error': 'Onboarding already in progress'}, status=409)

    username = request.user.username
    q = queue_module.Queue()
    onboard_queues[project_name] = q

    # Resolve ports now (in the request thread) to avoid closure scoping issues
    if odoo_port and db_port:
        resolved_odoo_port = int(odoo_port)
        resolved_db_port   = int(db_port)
    else:
        resolved_odoo_port, resolved_db_port = onboard_service.get_next_ports()

    # ── Phases definition (sent once so the frontend can initialise the tracker)
    PHASES = [
        {'id': 'ports',    'label': 'Assigning ports'},
        {'id': 'clone',    'label': 'Cloning repository'},
        {'id': 'addons',   'label': 'Detecting addons'},
        {'id': 'config',   'label': 'Writing configuration'},
        {'id': 'build',    'label': 'Building Docker image'},
        {'id': 'start',    'label': 'Starting containers'},
        {'id': 'register', 'label': 'Registering project'},
    ]

    def onboard_worker():
        def emit(event: dict):
            q.put(event)

        odoo_port = resolved_odoo_port
        db_port   = resolved_db_port

        try:
            # Announce phases upfront so the UI can render the full tracker immediately
            emit({'type': 'phases', 'phases': PHASES})

            # ── ports ──────────────────────────────────────────────
            emit({'type': 'phase_start', 'phase': 'ports'})
            emit({'type': 'log', 'text': f'Odoo port: {odoo_port}  ·  DB port: {db_port}'})
            emit({'type': 'phase_done', 'phase': 'ports'})

            # ── clone ──────────────────────────────────────────────
            emit({'type': 'phase_start', 'phase': 'clone'})
            success, repo_dir = onboard_service.clone_repository(repo_url, project_name, emit)
            if not success:
                emit({'type': 'phase_error', 'phase': 'clone', 'message': repo_dir})
                emit({'type': 'done', 'success': False})
                return
            emit({'type': 'phase_done', 'phase': 'clone'})

            # ── addons ─────────────────────────────────────────────
            emit({'type': 'phase_start', 'phase': 'addons'})
            addons = onboard_service.detect_addons(repo_dir)
            if addons:
                preview = ', '.join(addons[:4]) + (f' … +{len(addons)-4} more' if len(addons) > 4 else '')
                emit({'type': 'log', 'text': f'Found {len(addons)} addon(s): {preview}'})
            else:
                emit({'type': 'log', 'text': 'No addons detected'})
            addons_path = onboard_service.build_addons_path(version, hr_base_mode)
            emit({'type': 'phase_done', 'phase': 'addons'})

            # ── config ─────────────────────────────────────────────
            emit({'type': 'phase_start', 'phase': 'config'})
            onboard_service.create_docker_stack(
                project_name, version, odoo_port, db_port,
                addons_path, hr_base_mode, repo_dir, emit,
            )
            emit({'type': 'phase_done', 'phase': 'config'})

            # ── build ──────────────────────────────────────────────
            emit({'type': 'phase_start', 'phase': 'build'})
            onboard_service.build_docker_image(project_name, emit)
            emit({'type': 'phase_done', 'phase': 'build'})

            # ── start ──────────────────────────────────────────────
            emit({'type': 'phase_start', 'phase': 'start'})
            onboard_service.start_containers(project_name, emit)
            emit({'type': 'phase_done', 'phase': 'start'})

            # ── register ───────────────────────────────────────────
            emit({'type': 'phase_start', 'phase': 'register'})
            onboard_service.update_registry(project_name, version, odoo_port, db_port, subdomain)
            emit({'type': 'log', 'text': 'Registry updated'})
            onboard_service.update_dozzle(project_name, emit)
            emit({'type': 'phase_done', 'phase': 'register'})

            # ── manual steps ───────────────────────────────────────
            onboard_service.configure_nginx(project_name, subdomain, odoo_port, emit)
            onboard_service.configure_cloudflare(subdomain, emit)

            # ── done ───────────────────────────────────────────────
            repo_detail = repo_url or 'no repo'
            AuditLog.objects.create(project=project_name, action='onboard',
                                    detail=f'{repo_detail} (v{version})', outcome='success', user=username)
            emit({'type': 'done', 'success': True, 'url': f'https://{subdomain}.zedev.org'})

        except Exception as e:
            repo_detail = repo_url or 'no repo'
            AuditLog.objects.create(project=project_name, action='onboard',
                                    detail=f'{repo_detail} (v{version})', outcome='failed', user=username)
            emit({'type': 'log', 'text': str(e), 'error': True})
            emit({'type': 'done', 'success': False})
            # Clean up partial project directory so re-onboarding is possible
            onboard_service.cleanup_project(project_name, emit)
        finally:
            q.put(None)   # sentinel — stream ends

    threading.Thread(target=onboard_worker, daemon=True).start()

    return JsonResponse({'success': True, 'project_name': project_name})


# ── SSE stream ───────────────────────────────────────────────────────

async def stream_onboard(request, project_name):
    async def generate():
        q = onboard_queues.get(project_name)
        if q is None:
            yield _sse({'type': 'done', 'success': False, 'error': 'No onboarding in progress'})
            return

        loop = asyncio.get_running_loop()
        try:
            while True:
                try:
                    event = await loop.run_in_executor(None, lambda: q.get(timeout=600))
                    if event is None:          # sentinel — worker finished
                        break
                    yield _sse(event)
                    if event.get('type') == 'done':
                        break
                except queue_module.Empty:
                    yield _sse({'type': 'done', 'success': False, 'error': 'Timed out waiting for output'})
                    break
        finally:
            onboard_queues.pop(project_name, None)

    return _sse_response(generate())
