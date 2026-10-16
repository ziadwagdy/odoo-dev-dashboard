from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from core.permissions import IsAdmin
from services import webpush as webpush_service
from .models import PushSubscription


@api_view(['GET'])
@permission_classes([IsAdmin])
def public_key(request):
    return Response({'key': webpush_service.public_key()})


@api_view(['POST'])
@permission_classes([IsAdmin])
def subscribe(request):
    endpoint = str(request.data.get('endpoint', ''))
    keys = request.data.get('keys') or {}
    if not endpoint.startswith('https://') or not keys.get('p256dh') or not keys.get('auth'):
        return Response({'error': 'invalid push subscription'}, status=400)
    PushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={'user': request.user, 'p256dh': keys['p256dh'], 'auth': keys['auth'],
                  'user_agent': request.META.get('HTTP_USER_AGENT', '')[:300]})
    return Response({'ok': True})


@api_view(['POST'])
@permission_classes([IsAdmin])
def unsubscribe(request):
    PushSubscription.objects.filter(user=request.user, endpoint=str(request.data.get('endpoint', ''))).delete()
    return Response({'ok': True})


@api_view(['POST'])
@permission_classes([IsAdmin])
def test_notification(request):
    n = webpush_service.send_to_user(request.user, 'Test notification',
                                     'Push notifications from the dashboard work on this device.')
    return Response({'ok': True, 'delivered': n})
