import asyncio
import json
import queue as queue_module
import threading

import psutil
from django.http import StreamingHttpResponse

from asgiref.sync import sync_to_async
import os

from django.conf import settings

from services import lifecycle
from services.registry import read_registry, get_project
from services.stream_auth import sse_auth
from apps.projects.models import UserProjectAssignment


async def _allowed_names(user):
    if not user or not user.is_authenticated:
        return None
    is_admin = await sync_to_async(lambda: user.groups.filter(name='admin').exists())()
    if is_admin:
        return None
    return await sync_to_async(
        lambda: set(UserProjectAssignment.objects.filter(user=user).values_list('project_name', flat=True))
    )()
from services.docker_service import get_container_status, get_container_logs, exec_in_container, get_docker_client
from services.health_service import get_host_stats, get_all_container_stats
from state import deploy_queues, branch_switch_queues, submodule_queues, submodule_switch_queues, pull_queues


def _sse(data: dict) -> str:
    return f'data: {json.dumps(data)}\n\n'


def _sse_response(async_gen):
    response = StreamingHttpResponse(async_gen, content_type='text/event-stream')
    response['X-Accel-Buffering'] = 'no'
    response['Cache-Control'] = 'no-cache'
    response['Connection'] = 'keep-alive'
    return response


@sse_auth()
async def stream_status(request):
    allowed = await _allowed_names(getattr(request, 'user', None))

    async def generate():
        loop = asyncio.get_running_loop()
        while True:
            projects = read_registry()
            if allowed is not None:
                projects = [p for p in projects if p['name'] in allowed]
            payload = []
            for p in projects:
                status = await loop.run_in_executor(None, lambda c=p['container']: get_container_status(c))
                payload.append({
                    'name': p['name'], 'container': p['container'],
                    'status': status, 'running': status == 'running',
                })
            yield _sse(payload)
            await asyncio.sleep(3)
    return _sse_response(generate())


@sse_auth(project_arg='name')
async def stream_deploy(request, name):
    async def generate():
        q = deploy_queues.get(name)
        if q is None:
            yield _sse({'line': 'No deploy in progress.', 'done': True})
            return
        loop = asyncio.get_running_loop()
        try:
            while True:
                try:
                    line = await loop.run_in_executor(None, lambda: q.get(timeout=60))
                    if line is None:
                        yield _sse({'line': '', 'done': True})
                        break
                    yield _sse({'line': line, 'done': False})
                except queue_module.Empty:
                    yield _sse({'line': '(timeout waiting for output)', 'done': True})
                    break
        finally:
            deploy_queues.pop(name, None)
    return _sse_response(generate())


@sse_auth(container_arg='name')
async def stream_logs(request, name):
    tail = int(request.GET.get('tail', 500))
    follow = request.GET.get('follow', 'true').lower() == 'true'

    async def generate():
        loop = asyncio.get_running_loop()
        log_queue: asyncio.Queue = asyncio.Queue()

        def _stream():
            try:
                for chunk in get_container_logs(name, tail=tail, follow=follow):
                    line = chunk.decode('utf-8', errors='replace').rstrip('\n\r')
                    if line:
                        loop.call_soon_threadsafe(log_queue.put_nowait, line)
            finally:
                loop.call_soon_threadsafe(log_queue.put_nowait, None)

        threading.Thread(target=_stream, daemon=True).start()

        while True:
            line = await log_queue.get()
            if line is None:
                break
            yield _sse({'line': line})

    return _sse_response(generate())


@sse_auth(container_arg='container_name')
async def stream_stats(request, container_name):
    async def generate():
        loop = asyncio.get_running_loop()
        stats_queue: asyncio.Queue = asyncio.Queue()

        def _stream():
            try:
                client = get_docker_client()
                container = client.containers.get(container_name)
                prev = None
                for stats in container.stats(stream=True, decode=True):
                    if prev is None:
                        prev = stats
                        loop.call_soon_threadsafe(
                            stats_queue.put_nowait,
                            {'cpu_pct': None, 'mem_used_mb': None, 'mem_limit_mb': None}
                        )
                        continue
                    cpu_delta = (
                        stats['cpu_stats']['cpu_usage']['total_usage']
                        - prev['cpu_stats']['cpu_usage']['total_usage']
                    )
                    sys_delta = (
                        stats['cpu_stats'].get('system_cpu_usage', 0)
                        - prev['cpu_stats'].get('system_cpu_usage', 0)
                    )
                    num_cpus = stats['cpu_stats'].get('online_cpus', 1)
                    cpu_pct = round((cpu_delta / sys_delta) * num_cpus * 100, 1) if sys_delta > 0 else 0.0
                    mem = stats['memory_stats']
                    mem_used = (mem.get('usage', 0) - mem.get('stats', {}).get('cache', 0)) / 1024 / 1024
                    mem_limit = mem.get('limit', 1) / 1024 / 1024
                    loop.call_soon_threadsafe(
                        stats_queue.put_nowait,
                        {'cpu_pct': cpu_pct, 'mem_used_mb': round(mem_used, 1), 'mem_limit_mb': round(mem_limit, 1)}
                    )
                    prev = stats
            except Exception as e:
                loop.call_soon_threadsafe(stats_queue.put_nowait, {'error': str(e)})

        threading.Thread(target=_stream, daemon=True).start()

        while True:
            data = await stats_queue.get()
            yield _sse(data)
            if 'error' in data:
                break

    return _sse_response(generate())


@sse_auth(project_arg='project', roles={'admin','manager'})
async def stream_module_update(request, project, dbname, module_name):
    """Update a module with a pre-update snapshot (see services/lifecycle.run_module_update)."""
    p = get_project(project)
    backup_dir = os.path.join(settings.DATA_DIR, 'backups', project)

    async def generate():
        loop = asyncio.get_running_loop()
        out_queue: asyncio.Queue = asyncio.Queue()

        def emit(line):
            loop.call_soon_threadsafe(out_queue.put_nowait, line)

        def _run():
            try:
                lifecycle.run_module_update(project, p['db_port'], dbname, module_name, emit, backup_dir)
            except Exception as e:
                emit(f'Update failed: {e}')
            finally:
                loop.call_soon_threadsafe(out_queue.put_nowait, None)

        threading.Thread(target=_run, daemon=True).start()

        while True:
            line = await out_queue.get()
            if line is None:
                yield _sse({'line': '', 'done': True})
                break
            yield _sse({'line': line, 'done': False})

    return _sse_response(generate())


@sse_auth(project_arg='project', roles={'admin','manager'})
async def stream_branch_switch(request, project):
    async def generate():
        loop = asyncio.get_running_loop()
        q = branch_switch_queues.get(project)
        if q is None:
            yield _sse({'line': 'No branch switch in progress.', 'done': True})
            return
        try:
            while True:
                try:
                    line = await loop.run_in_executor(None, lambda: q.get(timeout=60))
                    if line is None:
                        yield _sse({'line': '', 'done': True})
                        break
                    yield _sse({'line': line, 'done': False})
                except queue_module.Empty:
                    yield _sse({'line': '(timeout)', 'done': True})
                    break
        finally:
            branch_switch_queues.pop(project, None)
    return _sse_response(generate())


@sse_auth(project_arg='project', roles={'admin','manager'})
async def stream_submodule_update(request, project):
    async def generate():
        loop = asyncio.get_running_loop()
        q = submodule_queues.get(project)
        if q is None:
            yield _sse({'line': 'No submodule update in progress.', 'done': True})
            return
        try:
            while True:
                try:
                    line = await loop.run_in_executor(None, lambda: q.get(timeout=120))
                    if line is None:
                        yield _sse({'line': '', 'done': True})
                        break
                    yield _sse({'line': line, 'done': False})
                except queue_module.Empty:
                    yield _sse({'line': '(timeout)', 'done': True})
                    break
        finally:
            submodule_queues.pop(project, None)
    return _sse_response(generate())


@sse_auth(roles={'admin','manager'})
async def stream_submodule_switch(request, key):
    import urllib.parse
    decoded_key = urllib.parse.unquote(key)

    async def generate():
        loop = asyncio.get_running_loop()
        q = submodule_switch_queues.get(decoded_key)
        if q is None:
            yield _sse({'line': 'No submodule switch in progress.', 'done': True})
            return
        try:
            while True:
                try:
                    line = await loop.run_in_executor(None, lambda: q.get(timeout=60))
                    if line is None:
                        yield _sse({'line': '', 'done': True})
                        break
                    yield _sse({'line': line, 'done': False})
                except queue_module.Empty:
                    yield _sse({'line': '(timeout)', 'done': True})
                    break
        finally:
            submodule_switch_queues.pop(decoded_key, None)
    return _sse_response(generate())


@sse_auth(project_arg='project', roles={'admin','manager'})
async def stream_git_pull(request, project):
    async def generate():
        loop = asyncio.get_running_loop()
        q = pull_queues.get(project)
        if q is None:
            yield _sse({'line': 'No pull in progress.', 'done': True})
            return
        try:
            while True:
                try:
                    line = await loop.run_in_executor(None, lambda: q.get(timeout=60))
                    if line is None:
                        yield _sse({'line': '', 'done': True})
                        break
                    yield _sse({'line': line, 'done': False})
                except queue_module.Empty:
                    yield _sse({'line': '(timeout)', 'done': True})
                    break
        finally:
            pull_queues.pop(project, None)
    return _sse_response(generate())


@sse_auth(roles={'admin', 'manager'})
async def stream_health_host(request):
    async def generate():
        loop = asyncio.get_running_loop()
        # Prime cpu_percent baseline — first call always returns 0.0
        await loop.run_in_executor(None, lambda: psutil.cpu_percent(interval=0.5))
        while True:
            data = await loop.run_in_executor(None, get_host_stats)
            yield _sse(data)
            await asyncio.sleep(3)
    return _sse_response(generate())


@sse_auth()
async def stream_health_containers(request):
    allowed = await _allowed_names(getattr(request, 'user', None))

    async def generate():
        loop = asyncio.get_running_loop()
        while True:
            projects = read_registry()
            if allowed is not None:
                projects = [p for p in projects if p['name'] in allowed]
            stats = await loop.run_in_executor(
                None, lambda: get_all_container_stats(projects)
            )
            yield _sse(stats)
            await asyncio.sleep(3)
    return _sse_response(generate())
