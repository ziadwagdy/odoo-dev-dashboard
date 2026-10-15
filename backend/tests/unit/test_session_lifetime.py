import datetime as dt

import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from freezegun import freeze_time
from rest_framework.authtoken.models import Token

from core import authentication as auth


@pytest.fixture
def token(db):
    user = User.objects.create_user('sess-user', password='x' * 16)
    return Token.objects.create(user=user)


def test_fresh_token_is_live(token):
    assert auth.token_is_live(token)


def test_absolute_lifetime_is_enforced(token):
    with freeze_time(timezone.now() + dt.timedelta(seconds=auth.ABSOLUTE_TTL + 5)):
        assert not auth.token_is_live(token)


def test_idle_timeout_is_enforced(token):
    auth.mark_active(token.key)
    with freeze_time(timezone.now() + dt.timedelta(seconds=auth.IDLE_TTL + 5)):
        assert not auth.token_is_live(token)


def test_activity_extends_the_idle_window(token):
    start = timezone.now()
    auth.mark_active(token.key)
    with freeze_time(start + dt.timedelta(seconds=auth.IDLE_TTL - 60)):
        assert auth.token_is_live(token)            # refreshes the idle clock
    with freeze_time(start + dt.timedelta(seconds=2 * auth.IDLE_TTL - 120)):
        assert auth.token_is_live(token)            # still inside the refreshed window


def test_unknown_token_and_inactive_user_resolve_to_none(token):
    assert auth.user_for_token_key('nope') is None
    token.user.is_active = False
    token.user.save()
    assert auth.user_for_token_key(token.key) is None


def test_expired_token_is_deleted_on_lookup(token):
    with freeze_time(timezone.now() + dt.timedelta(seconds=auth.ABSOLUTE_TTL + 5)):
        assert auth.user_for_token_key(token.key) is None
    assert not Token.objects.filter(key=token.key).exists()
