"""Who may sign in to which Odoo database as whom ("Open as").

Pure function, no I/O: the whole role x target x database-state matrix is unit tested.

Rules (least privilege, production-like databases are the exception that needs a reason):
  developer  ordinary users, neutralized databases only, no reason needed
  manager    ordinary users anywhere (reason if the database is not neutralized);
             administrators only in neutralized databases, with a reason
  admin      anything (reason if the database is not neutralized)
  anyone else (no role, unknown role): denied
"""
from dataclasses import dataclass

MIN_REASON_LENGTH = 8


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason_required: bool = False
    message: str = ''
    satisfied: bool = False        # allowed AND (no reason needed OR a meaningful reason was given)


def _decision(allowed, reason_required, message, reason):
    meaningful = len((reason or '').strip()) >= MIN_REASON_LENGTH
    return Decision(allowed, reason_required, message,
                    satisfied=allowed and (not reason_required or meaningful))


def can_open_as(role, *, target_is_admin, db_neutralized, reason=''):
    if role == 'admin':
        return _decision(True, not db_neutralized, '', reason)

    if role == 'manager':
        if target_is_admin and not db_neutralized:
            return _decision(False, False,
                             'Signing in as an administrator of a database that is not neutralized is limited to admins.',
                             reason)
        return _decision(True, target_is_admin or not db_neutralized, '', reason)

    if role == 'developer':
        if target_is_admin:
            return _decision(False, False, 'Only managers and admins may sign in as an administrator.', reason)
        if not db_neutralized:
            return _decision(False, False,
                             'This database is not neutralized (it may hold live data and integrations). '
                             'Ask a manager.', reason)
        return _decision(True, False, '', reason)

    return _decision(False, False, 'Your role does not allow signing in to databases.', reason)
