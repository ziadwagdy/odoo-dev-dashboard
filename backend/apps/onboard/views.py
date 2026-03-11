import asyncio
import json
import queue as queue_module
import threading

from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view

from services import onboard_service
from state import onboard_queues


def _sse(data: dict) -> str:
    return f'data: {json.dumps(data)}\n\n'


def _sse_response(async_gen):
    response = StreamingHttpResponse(async_gen, content_type='text/event-stream')
    response['X-Accel-Buffering'] = 'no'
    response['Cache-Control'] = 'no-cache'
    response['Connection'] = 'keep-alive'
    return response


@api_view(['POST'])
def validate_project(request):
    """Validate project configuration before onboarding."""
    data = request.data
    
    project_name = data.get('project_name', '').strip()
    subdomain = data.get('subdomain', '').strip()
    version = data.get('version')
    
    errors = {}
    
    # Validate project name
    valid, error = onboard_service.validate_project_name(project_name)
    if not valid:
        errors['project_name'] = error
    elif onboard_service.check_project_exists(project_name):
        errors['project_name'] = f"Project '{project_name}' already exists"
    
    # Validate subdomain
    valid, error = onboard_service.validate_subdomain(subdomain)
    if not valid:
        errors['subdomain'] = error
    
    # Check worktrees
    if version and not onboard_service.check_worktrees_exist(version):
        errors['version'] = f"Worktrees for Odoo {version} not found"
    
    # Get next available ports
    try:
        odoo_port, db_port = onboard_service.get_next_ports()
    except Exception as e:
        return JsonResponse({'valid': False, 'errors': {'general': str(e)}}, status=500)
    
    if errors:
        return JsonResponse({'valid': False, 'errors': errors}, status=400)
    
    return JsonResponse({
        'valid': True,
        'assigned_ports': {
            'odoo_port': odoo_port,
            'db_port': db_port
        }
    })


@api_view(['POST'])
def start_onboard(request):
    """Start the onboarding process in a background thread."""
    data = request.data
    
    project_name = data.get('project_name')
    repo_url = data.get('repo_url')
    version = data.get('version')
    subdomain = data.get('subdomain')
    hr_base_mode = data.get('hr_base_mode', 'no')
    
    # Validate required fields
    if not all([project_name, repo_url, version, subdomain]):
        return JsonResponse({
            'success': False,
            'error': 'Missing required fields'
        }, status=400)
    
    # Check if already onboarding
    if project_name in onboard_queues:
        return JsonResponse({
            'success': False,
            'error': 'Onboarding already in progress for this project'
        }, status=409)
    
    # Create queue for streaming progress
    q = queue_module.Queue()
    onboard_queues[project_name] = q
    
    def onboard_worker():
        """Background thread to perform onboarding."""
        def progress(msg):
            q.put(msg)
        
        try:
            # Get ports
            odoo_port, db_port = onboard_service.get_next_ports()
            progress(f"Assigned ports: Odoo={odoo_port}, DB={db_port}")
            
            # Clone repository
            progress("Starting repository clone...")
            success, repo_dir = onboard_service.clone_repository(
                repo_url, project_name, progress
            )
            
            if not success:
                progress(f"ERROR: {repo_dir}")
                q.put(None)
                return
            
            # Detect addons
            progress("Detecting addon modules...")
            addons = onboard_service.detect_addons(repo_dir)
            if addons:
                progress(f"Found {len(addons)} addon(s): {', '.join(addons[:5])}" +
                        (f" and {len(addons)-5} more" if len(addons) > 5 else ""))
            else:
                progress("No addons detected")
            
            # Build addons path
            addons_path = onboard_service.build_addons_path(version, hr_base_mode)
            progress(f"Addons path: {addons_path}")
            
            # Create Docker stack
            progress("Creating Docker configuration...")
            onboard_service.create_docker_stack(
                project_name, version, odoo_port, db_port,
                addons_path, hr_base_mode, repo_dir, progress
            )
            
            # Build Docker image
            onboard_service.build_docker_image(project_name, progress)
            
            # Start containers
            onboard_service.start_containers(project_name, progress)
            
            # Configure Cloudflare tunnel
            progress("Configuring public URL...")
            cf_success = onboard_service.configure_cloudflare(subdomain, odoo_port, progress)
            
            # Update registry
            progress("Updating project registry...")
            onboard_service.update_registry(project_name, version, odoo_port, db_port, subdomain)
            progress("Registry updated")
            
            # Success
            progress(f"SUCCESS: Project onboarded at https://{subdomain}.zedev.org")
            if not cf_success:
                progress("WARNING: Cloudflare tunnel configuration failed - manual setup required")
            
        except Exception as e:
            progress(f"ERROR: {str(e)}")
        finally:
            q.put(None)
    
    # Start background thread
    thread = threading.Thread(target=onboard_worker, daemon=True)
    thread.start()
    
    return JsonResponse({
        'success': True,
        'project_name': project_name
    })


async def stream_onboard(request, project_name):
    """Stream onboarding progress via SSE."""
    async def generate():
        q = onboard_queues.get(project_name)
        if q is None:
            yield _sse({'line': 'No onboarding in progress.', 'done': True})
            return
        
        loop = asyncio.get_running_loop()
        try:
            while True:
                try:
                    line = await loop.run_in_executor(None, lambda: q.get(timeout=300))
                    if line is None:
                        yield _sse({'line': '', 'done': True})
                        break
                    
                    # Check if it's an error or success message
                    is_error = line.startswith('ERROR:')
                    is_success = line.startswith('SUCCESS:')
                    is_warning = line.startswith('WARNING:')
                    
                    yield _sse({
                        'line': line,
                        'done': False,
                        'error': is_error,
                        'success': is_success,
                        'warning': is_warning
                    })
                except queue_module.Empty:
                    yield _sse({'line': '(timeout waiting for output)', 'done': True, 'error': True})
                    break
        finally:
            onboard_queues.pop(project_name, None)
    
    return _sse_response(generate())
