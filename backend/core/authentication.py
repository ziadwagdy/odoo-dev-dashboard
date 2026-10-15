"""Session validation for the dashboard API, SSE streams and notebook WebSocket.

DRF tokens never expire by themselves. This adds:
  * an absolute lifetime measured from the login that created the token, and
  * an idle timeout measured from the last authenticated request,
and one shared validation function so DRF views, SSE views and the WebSocket
consumer all enforce exactly the same rules.
"""
import os
import time

from django.core.cache import cache
from django.utils import timezone
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import AuthenticationFailed

ABSOLUTE_TTL = int(os.environ.get('SESSION_MAX_HOURS', '12')) * 3600
IDLE_TTL = int(os.environ.get('SESSION_IDLE_MINUTES', '120')) * 60


def _last_seen_key(token_key: str) -> str:
    return f'session:last:{token_key}'


def mark_active(token_key: str) -> None:
    cache.set(_last_seen_key(token_key), time.time(), None)


def token_is_live(token: Token) -> bool:
    """True if the token is inside both lifetimes; refreshes the idle clock."""
    if (timezone.now() - token.created).total_seconds() > ABSOLUTE_TTL:
        return False
    now = time.time()
    last = cache.get(_last_seen_key(token.key))
    # no record (process restarted) -> start the idle clock now rather than log everyone out
    if last is not None and now - last > IDLE_TTL:
        return False
    mark_active(token.key)
    return True


def user_for_token_key(key: str):
    """Return the active user for a raw token key, or None (also deletes expired tokens)."""
    if not key:
        return None
    try:
        token = Token.objects.select_related('user').get(key=key)
    except Token.DoesNotExist:
        return None
    if not token.user.is_active:
        return None
    if not token_is_live(token):
        token.delete()
        return None
    return token.user


class ExpiringTokenAuthentication(TokenAuthentication):
    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)
        if not token_is_live(token):
            token.delete()
            raise AuthenticationFailed('Session expired — please sign in again.')
        return user, token
