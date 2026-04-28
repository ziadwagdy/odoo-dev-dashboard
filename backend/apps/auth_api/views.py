from django.contrib.auth import authenticate
from django.contrib.auth.models import User, Group
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from core.permissions import IsAdmin
from apps.projects.models import AuditLog, UserProjectAssignment
from apps.projects.serializers import AuditLogSerializer


def _audit(action, detail='', outcome='success', user=''):
    try:
        AuditLog.objects.create(project='system', action=action, detail=detail, outcome=outcome, user=user)
    except Exception:
        pass


def _user_role(user):
    if user.groups.filter(name='admin').exists():
        return 'admin'
    if user.groups.filter(name='manager').exists():
        return 'manager'
    if user.groups.filter(name='developer').exists():
        return 'developer'
    return 'viewer'


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '')
    if not username or not password:
        return Response({'error': 'username and password required'}, status=400)

    user = authenticate(username=username, password=password)
    if user is None:
        return Response({'error': 'Invalid credentials'}, status=401)

    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'username': user.username, 'role': _user_role(user)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    request.user.auth_token.delete()
    return Response({'ok': True})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    return Response({'username': request.user.username, 'role': _user_role(request.user)})


@api_view(['GET'])
@permission_classes([IsAdmin])
def list_users(request):
    users = User.objects.prefetch_related('groups', 'project_assignments').all().order_by('username')
    data = []
    for u in users:
        data.append({
            'id': u.id,
            'username': u.username,
            'role': _user_role(u),
            'is_active': u.is_active,
            'date_joined': u.date_joined,
            'last_login': u.last_login,
            'assigned_projects': list(u.project_assignments.values_list('project_name', flat=True)),
        })
    return Response({'users': data})


@api_view(['POST'])
@permission_classes([IsAdmin])
def create_user(request):
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '')
    role = request.data.get('role', 'developer')

    if not username or not password:
        return Response({'error': 'username and password required'}, status=400)
    if role not in ('admin', 'manager', 'developer'):
        return Response({'error': 'role must be admin, manager, or developer'}, status=400)
    if User.objects.filter(username=username).exists():
        return Response({'error': f'User {username!r} already exists'}, status=400)

    user = User.objects.create_user(username=username, password=password)
    group = Group.objects.get(name=role)
    user.groups.add(group)
    if role != 'admin':
        from services.registry import read_registry
        projects = read_registry()
        UserProjectAssignment.objects.bulk_create([
            UserProjectAssignment(user=user, project_name=p['name']) for p in projects
        ], ignore_conflicts=True)
    _audit('user_create', f'{username} as {role}', user=request.user.username)
    return Response({'ok': True, 'username': user.username, 'role': role}, status=201)


@api_view(['DELETE'])
@permission_classes([IsAdmin])
def delete_user(request, user_id):
    if request.user.id == user_id:
        return Response({'error': 'Cannot delete your own account'}, status=400)
    try:
        user = User.objects.get(id=user_id)
        deleted_username = user.username
        user.delete()
        _audit('user_delete', deleted_username, user=request.user.username)
        return Response({'ok': True})
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request, user_id):
    # Admins can change anyone's password; users can only change their own
    if request.user.id != user_id and not request.user.groups.filter(name='admin').exists():
        return Response({'error': 'Admin privileges required.'}, status=403)
    new_password = request.data.get('password', '').strip()
    if len(new_password) < 6:
        return Response({'error': 'Password must be at least 6 characters'}, status=400)
    try:
        user = User.objects.get(id=user_id)
        user.set_password(new_password)
        user.save()
        # Invalidate existing token so they must log in again
        Token.objects.filter(user=user).delete()
        _audit('password_change', user.username, user=request.user.username)
        return Response({'ok': True})
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)


@api_view(['POST'])
@permission_classes([IsAdmin])
def update_user_role(request, user_id):
    role = request.data.get('role', '')
    if role not in ('admin', 'manager', 'developer'):
        return Response({'error': 'role must be admin, manager, or developer'}, status=400)
    try:
        user = User.objects.get(id=user_id)
        user.groups.clear()
        user.groups.add(Group.objects.get(name=role))
        _audit('user_role_change', f'{user.username} → {role}', user=request.user.username)
        return Response({'ok': True, 'role': role})
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)


@api_view(['GET'])
@permission_classes([IsAdmin])
def system_audit(request):
    records = AuditLog.objects.filter(project='system')[:50]
    return Response(AuditLogSerializer(records, many=True).data)


@api_view(['GET', 'POST'])
@permission_classes([IsAdmin])
def user_project_assignments(request, user_id):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)

    if request.method == 'GET':
        names = list(UserProjectAssignment.objects.filter(user=user).values_list('project_name', flat=True))
        return Response({'projects': names})

    projects = request.data.get('projects', [])
    if not isinstance(projects, list):
        return Response({'error': 'projects must be a list'}, status=400)
    UserProjectAssignment.objects.filter(user=user).delete()
    UserProjectAssignment.objects.bulk_create([
        UserProjectAssignment(user=user, project_name=n) for n in projects
    ])
    _audit('user_projects_assign', f'{user.username}: {projects}', user=request.user.username)
    return Response({'ok': True, 'projects': projects})
