import queue
import threading

from rest_framework.decorators import api_view
from rest_framework.response import Response

from services.registry import get_project
from services.git_service import list_branches, switch_branch, get_submodule_status, update_submodules, git_pull
from state import branch_switch_queues, submodule_queues, pull_queues


@api_view(['GET'])
def git_branches(request, project):
    p = get_project(project)
    if not p or not p.get('folder'):
        return Response({'error': 'project not found'}, status=404)
    result = list_branches(p['folder'])
    return Response(result)


@api_view(['POST'])
def git_switch(request, project):
    p = get_project(project)
    if not p or not p.get('folder'):
        return Response({'error': 'project not found'}, status=404)
    branch = (request.data.get('branch') or '').strip()
    if not branch:
        return Response({'error': 'branch required'}, status=400)

    q = queue.Queue()
    branch_switch_queues[project] = q

    def _run():
        switch_branch(p['folder'], branch, q)

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
def git_submodule_update(request, project):
    p = get_project(project)
    if not p or not p.get('folder'):
        return Response({'error': 'project not found'}, status=404)

    q = queue.Queue()
    submodule_queues[project] = q

    def _run():
        update_submodules(p['folder'], q)

    threading.Thread(target=_run, daemon=True).start()
    return Response({'ok': True, 'stream_url': f'/stream/submodule-update/{project}'})


@api_view(['POST'])
def git_pull_view(request, project):
    p = get_project(project)
    if not p or not p.get('folder'):
        return Response({'error': 'project not found'}, status=404)

    q = queue.Queue()
    pull_queues[project] = q

    def _run():
        git_pull(p['folder'], q)

    threading.Thread(target=_run, daemon=True).start()
    return Response({'ok': True, 'stream_url': f'/stream/git-pull/{project}'})
