"""Authentication/authorisation for the plain-Django SSE and Channels WebSocket
endpoints, which sit outside DRF and therefore had no auth at all.

EventSource and WebSocket cannot send an Authorization header from the browser,
so the DRF token is accepted from either the header or a ``token`` query
parameter (the nginx locations for /stream/ and /ws/ log the path only, never
the query string).
"""
import re
from functools import wraps
from urllib.parse import parse_qs

from asgiref.sync import sync_to_async
from django.http import JsonResponse
from rest_framework.authtoken.models import Token

from services.registry import read_registry
from apps.projects.models import UserProjectAssignment

# names that end up in docker exec commands / queue keys / file paths
SAFE_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.,-]{0,127}$')


def _lookup_user(key):
    if not key:
        return None
    try:
        user = Token.objects.select_related('user').get(key=key).user
    except Token.DoesNotExist:
        return None
    return user if user.is_active else None


def _token_from_request(request):
    header = request.META.get('HTTP_AUTHORIZATION', '')
    if header.lower().startswith('token '):
        return header.split(' ', 1)[1].strip()
    return request.GET.get('token', '')


def token_from_scope(scope):
    query = parse_qs(scope.get('query_string', b'').decode('latin-1'))
    return (query.get('token') or [''])[0]


async def user_from_request(request):
    return await sync_to_async(_lookup_user)(_token_from_request(request))


async def user_from_token(key):
    return await sync_to_async(_lookup_user)(key)


def _groups(user):
    return set(user.groups.values_list('name', flat=True))


async def role_names(user):
    return await sync_to_async(_groups)(user)


async def allowed_projects(user):
    """None -> every project (admin); otherwise the set of assigned project names."""
    groups = await role_names(user)
    if 'admin' in groups:
        return None
    return await sync_to_async(
        lambda: set(UserProjectAssignment.objects.filter(user=user).values_list('project_name', flat=True))
    )()


def _registry_names():
    return {p['name'] for p in read_registry()}


def project_from_container(name):
    for suffix in ('-app', '-db'):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def sse_auth(project_arg=None, container_arg=None, roles=None):
    """Decorator for async SSE views.

    project_arg   – kwarg holding a registry project name (ACL + registry check)
    container_arg – kwarg holding a container name; mapped to its project
    roles         – optional set of group names of which the user needs one
    """
    def deco(view):
        @wraps(view)
        async def wrapper(request, *args, **kwargs):
            for k, v in kwargs.items():
                if k != 'key' and not SAFE_NAME.match(str(v)):
                    return JsonResponse({'error': 'invalid parameter'}, status=400)
            user = await user_from_request(request)
            if user is None:
                return JsonResponse({'error': 'authentication required'}, status=401)
            request.user = user
            groups = await role_names(user)
            if roles and not (groups & set(roles)):
                return JsonResponse({'error': 'insufficient privileges'}, status=403)
            project = None
            if project_arg:
                project = kwargs.get(project_arg)
            elif container_arg:
                project = project_from_container(kwargs.get(container_arg, ''))
                if project not in await sync_to_async(_registry_names)():
                    # not a project container (dozzle, dashboard, ...): admins only
                    if 'admin' not in groups:
                        return JsonResponse({'error': 'insufficient privileges'}, status=403)
                    project = None
            if project:
                if project not in await sync_to_async(_registry_names)():
                    return JsonResponse({'error': 'unknown project'}, status=404)
                allowed = await allowed_projects(user)
                if allowed is not None and project not in allowed:
                    return JsonResponse({'error': 'not allowed for this project'}, status=403)
            return await view(request, *args, **kwargs)
        return wrapper
    return deco
