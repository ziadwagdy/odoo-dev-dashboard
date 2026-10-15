"""Who may sign in to which Odoo database as whom (the 'Open as' policy).

Written before the implementation (Phase 1). The policy is a pure function so the whole
role x target x database-state matrix can be checked exhaustively.
"""
import itertools

import pytest

from services.access_policy import Decision, can_open_as

ROLES = ['admin', 'manager', 'developer']


def decide(role, admin_target, neutralized, reason=''):
    return can_open_as(role, target_is_admin=admin_target, db_neutralized=neutralized, reason=reason)


def test_decision_has_allowed_and_reason_required():
    d = decide('admin', False, True)
    assert isinstance(d, Decision) and d.allowed is True and d.reason_required is False


# ── developers: ordinary users in neutralized databases only ───────────────
def test_developer_may_open_ordinary_user_in_neutralized_db_without_reason():
    d = decide('developer', admin_target=False, neutralized=True)
    assert d.allowed and not d.reason_required


def test_developer_may_not_open_an_administrator():
    d = decide('developer', admin_target=True, neutralized=True)
    assert not d.allowed and 'manager' in d.message.lower()


def test_developer_may_not_open_a_database_that_is_not_neutralized():
    d = decide('developer', admin_target=False, neutralized=False)
    assert not d.allowed and 'neutraliz' in d.message.lower()


# ── managers: administrators only in neutralized databases, with a reason ──
def test_manager_ordinary_user_neutralized_needs_no_reason():
    d = decide('manager', False, True)
    assert d.allowed and not d.reason_required


def test_manager_ordinary_user_in_non_neutralized_db_needs_a_reason():
    d = decide('manager', False, False)
    assert d.allowed and d.reason_required


def test_manager_administrator_in_neutralized_db_needs_a_reason():
    d = decide('manager', True, True)
    assert d.allowed and d.reason_required


def test_manager_may_not_open_an_administrator_of_a_non_neutralized_db():
    d = decide('manager', True, False)
    assert not d.allowed


# ── admins: everything, but production-like databases need a reason ────────
def test_admin_neutralized_db_needs_no_reason_even_for_admin_target():
    d = decide('admin', True, True)
    assert d.allowed and not d.reason_required


def test_admin_non_neutralized_db_needs_a_reason():
    d = decide('admin', True, False)
    assert d.allowed and d.reason_required


# ── reasons ───────────────────────────────────────────────────────────────
def test_a_required_reason_must_be_meaningful():
    assert not decide('admin', False, False, reason='').satisfied
    assert not decide('admin', False, False, reason='ok').satisfied
    assert not decide('admin', False, False, reason='   ').satisfied
    assert decide('admin', False, False, reason='customer ticket #4521 repro').satisfied


def test_satisfied_is_true_when_no_reason_is_needed():
    assert decide('developer', False, True).satisfied


def test_a_denied_decision_is_never_satisfied_even_with_a_reason():
    assert not decide('developer', True, True, reason='please let me in, I promise').satisfied


# ── unknown roles fail closed ─────────────────────────────────────────────
@pytest.mark.parametrize('role', ['viewer', '', None, 'root', 'ADMIN'])
def test_unknown_roles_are_denied(role):
    d = decide(role, False, True)
    assert not d.allowed


def test_matrix_is_total_and_never_raises():
    for role, admin_target, neutralized in itertools.product(ROLES, [True, False], [True, False]):
        d = decide(role, admin_target, neutralized)
        assert isinstance(d.allowed, bool) and isinstance(d.reason_required, bool)
