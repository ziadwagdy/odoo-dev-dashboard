from rest_framework.decorators import api_view
from rest_framework.response import Response

from services.registry import get_project
from .kernel_manager import start_kernel, stop_kernel, get_kernel_status


@api_view(['GET'])
def kernel_status(request, project):
    return Response(get_kernel_status(project))


@api_view(['POST'])
def kernel_start(request, project):
    p = get_project(project)
    if not p:
        return Response({'error': 'project not found'}, status=404)
    db = request.data.get('db', '').strip()
    if not db:
        return Response({'error': 'db required'}, status=400)
    result = start_kernel(project, p['container'], db)
    return Response(result)


@api_view(['POST'])
def kernel_stop(request, project):
    return Response(stop_kernel(project))
