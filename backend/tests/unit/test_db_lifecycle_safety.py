"""Phase 2: neutralization is verified, new databases are locked down. Written first."""
import pytest

from services import db_service


def _render(q):
    """Render a psycopg2.sql Composable without a connection (identifiers double-quoted)."""
    from psycopg2 import sql as _sql
    if isinstance(q, _sql.Composed):
        return ''.join(_render(p) for p in q.seq)
    if isinstance(q, _sql.SQL):
        return q.string
    if isinstance(q, _sql.Identifier):
        return '"' + q.strings[0] + '"'
    return str(q)


class FakeCursor:
    def __init__(self, log, rows=None):
        self.log, self.rows = log, rows or []

    def execute(self, query, params=None):
        self.log.append(_render(query))

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class FakeConn:
    def __init__(self, log, rows=None):
        self.log, self.rows, self.autocommit = log, rows, False

    def cursor(self):
        return FakeCursor(self.log, self.rows)

    def close(self):
        pass

    def commit(self):
        pass


@pytest.fixture
def sqllog(monkeypatch):
    log = []
    monkeypatch.setattr(db_service, '_connect', lambda port, dbname='postgres': FakeConn(log))
    return log


# ── neutralization is verified, not assumed ────────────────────────────────
def test_neutralize_raises_when_the_flag_is_not_set_afterwards(monkeypatch):
    monkeypatch.setattr(db_service, 'exec_in_container_sync', lambda c, cmd: (0, b'Neutralization finished'))
    monkeypatch.setattr(db_service, 'database_state', lambda port, db: {'neutralized': False})
    with pytest.raises(RuntimeError, match='not neutralized'):
        db_service.neutralize_database('alpha', 'db1', db_port=15432)


def test_neutralize_succeeds_when_the_flag_is_set(monkeypatch):
    monkeypatch.setattr(db_service, 'exec_in_container_sync', lambda c, cmd: (0, b''))
    monkeypatch.setattr(db_service, 'database_state', lambda port, db: {'neutralized': True})
    db_service.neutralize_database('alpha', 'db1', db_port=15432)


def test_neutralize_still_reports_a_failed_command(monkeypatch):
    monkeypatch.setattr(db_service, 'exec_in_container_sync', lambda c, cmd: (1, b'Traceback ...'))
    with pytest.raises(RuntimeError, match='Neutralize failed'):
        db_service.neutralize_database('alpha', 'db1', db_port=15432)


def test_database_state_reads_the_odoo_flag(monkeypatch):
    log = []
    monkeypatch.setattr(db_service, '_connect', lambda port, dbname='postgres': FakeConn(log, rows=[('True',)]))
    assert db_service.database_state(15432, 'db1') == {'neutralized': True}
    monkeypatch.setattr(db_service, '_connect', lambda port, dbname='postgres': FakeConn(log, rows=[]))
    assert db_service.database_state(15432, 'db1') == {'neutralized': False}


# ── lock down ──────────────────────────────────────────────────────────────
def test_lock_down_revokes_public_connect_with_a_quoted_identifier(sqllog):
    db_service.lock_down_database(15432, 'my-db')
    joined = ' '.join(sqllog)
    assert 'REVOKE CONNECT ON DATABASE "my-db" FROM PUBLIC' in joined


def test_lock_down_rejects_unsafe_names(sqllog):
    with pytest.raises(ValueError):
        db_service.lock_down_database(15432, 'x"; DROP DATABASE y; --')
    assert sqllog == []


def test_restore_duplicate_and_create_all_neutralize_with_verification_then_lock_down(monkeypatch):
    order = []
    monkeypatch.setattr(db_service, '_connect', lambda port, dbname='postgres': FakeConn([]))
    monkeypatch.setattr(db_service, 'neutralize_database',
                        lambda project, dbname, db_port=None: order.append(('neutralize', dbname, db_port)))
    monkeypatch.setattr(db_service, 'lock_down_database', lambda port, dbname: order.append(('lock', dbname)))
    monkeypatch.setattr(db_service.subprocess, 'run',
                        lambda *a, **k: type('R', (), {'returncode': 0, 'stderr': '', 'stdout': ''})())
    monkeypatch.setattr(db_service, 'exec_in_container_sync', lambda c, cmd: (0, b''))
    monkeypatch.setattr(db_service, 'list_database_names', lambda port: [])
    monkeypatch.setattr(db_service, 'set_odoo_user_password', lambda *a, **k: 'pw')

    db_service.restore_database(15432, 'r1', '/tmp/x.dump', project_name='alpha')
    db_service.duplicate_database(15432, 'src', 'd1', project_name='alpha')
    db_service.create_odoo_database('alpha', 15432, 'c1')
    assert order == [('neutralize', 'r1', 15432), ('lock', 'r1'),
                     ('neutralize', 'd1', 15432), ('lock', 'd1'),
                     ('neutralize', 'c1', 15432), ('lock', 'c1')]
