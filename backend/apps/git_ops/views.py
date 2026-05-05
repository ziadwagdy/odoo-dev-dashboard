import queue
import threading

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import IsAdmin, IsAdminOrManager

from services.registry import get_project
from services.git_service import list_branches, switch_branch, get_submodule_status, update_submodules, git_pull, list_submodule_branches, switch_submodule_branch
from state import branch_switch_queues, submodule_queues, submodule_switch_queues, pull_queues
from apps.projects.models import AuditLog


def _audit(project, action, detail='', outcome='success', user=''):
    try:
        AuditLog.objects.create(project=project, action=action, detail=detail, outcome=outcome, user=user)
    except Exception:
        pass


@api_view(['GET'])
def git_branches(request, project):
    p = get_project(project)
    if not p or not p.get('folder'):
        return Response({'error': 'project not found'}, status=404)
    result = list_branches(p['folder'])
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAdminOrManager])
def git_switch(request, project):
    p = get_project(project)
    if not p or not p.get('folder'):
        return Response({'error': 'project not found'}, status=404)
    branch = (request.data.get('branch') or '').strip()
    if not branch:
        return Response({'error': 'branch required'}, status=400)

    username = request.user.username
    q = queue.Queue()
    branch_switch_queues[project] = q

    def _run():
        switch_branch(p['folder'], branch, q)
        _audit(project, 'branch_switch', branch, user=username)

    threading.Thread(target=_run, daemon=True).start()
    return Response({'ok': True, 'stream_url': f'/stream/branch-switch/{project}'})


@api_view(['GET'])
def git_submodules(request, project):
    p = get_project(project)
    if not p or not p.get('folder'):
        return Response({'error': 'project not found'}, status=404)
    result = get_submodule_status(p['folder'])
    return Response({'submodules': result})


@api_view(['POST'])
@permission_classes([IsAdminOrManager])
def git_submodule_update(request, project):
    p = get_project(project)
    if not p or not p.get('folder'):
        return Response({'error': 'project not found'}, status=404)

    username = request.user.username
    q = queue.Queue()
    submodule_queues[project] = q

    def _run():
        outcome = 'success'
        try:
            update_submodules(p['folder'], q)
        except Exception:
            outcome = 'failed'
        finally:
            _audit(project, 'submodule_update', '', outcome=outcome, user=username)

    threading.Thread(target=_run, daemon=True).start()
    return Response({'ok': True, 'stream_url': f'/stream/submodule-update/{project}'})


@api_view(['GET'])
def git_submodule_branches(request, project):
    p = get_project(project)
    if not p or not p.get('folder'):
        return Response({'error': 'project not found'}, status=404)
    sub_path = (request.GET.get('path') or '').strip()
    if not sub_path:
        return Response({'error': 'path required'}, status=400)
    result = list_submodule_branches(p['folder'], sub_path)
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAdminOrManager])
def git_submodule_switch(request, project):
    p = get_project(project)
    if not p or not p.get('folder'):
        return Response({'error': 'project not found'}, status=404)
    sub_path = (request.data.get('sub_path') or '').strip()
    branch = (request.data.get('branch') or '').strip()
    if not sub_path or not branch:
        return Response({'error': 'sub_path and branch required'}, status=400)

    username = request.user.username
    key = f'{project}:{sub_path}'
    q = queue.Queue()
    submodule_switch_queues[key] = q

    import urllib.parse
    encoded_key = urllib.parse.quote(key, safe='')

    def _run():
        switch_submodule_branch(p['folder'], sub_path, branch, q)
        _audit(project, 'submodule_branch_switch', f'{sub_path} → {branch}', user=username)

    threading.Thread(target=_run, daemon=True).start()
    return Response({'ok': True, 'stream_url': f'/stream/submodule-switch/{encoded_key}'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def git_pull_view(request, project):
    p = get_project(project)
    if not p or not p.get('folder'):
        return Response({'error': 'project not found'}, status=404)

    username = request.user.username
    q = queue.Queue()
    pull_queues[project] = q

    def _run():
        outcome = 'success'
        try:
            git_pull(p['folder'], q)
        except Exception:
            outcome = 'failed'
        finally:
            _audit(project, 'git_pull', '', outcome=outcome, user=username)

    threading.Thread(target=_run, daemon=True).start()
    return Response({'ok': True, 'stream_url': f'/stream/git-pull/{project}'})
