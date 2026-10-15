"""Pre-update snapshot, module update and restore test. Written first (Phase 2)."""
import os

import pytest

from services import lifecycle


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


@pytest.fixture
def fakes(monkeypatch, tmp_path):
    calls = []

    def fake_backup(port, db, directory):
        os.makedirs(directory, exist_ok=True)
        name = f'{db}-20261015-120000.dump'
        path = os.path.join(directory, name)
        open(path, 'w').write('dump')
        calls.append(('backup', db))
        return path, name

    monkeypatch.setattr(lifecycle, 'backup_database', fake_backup)
    monkeypatch.setattr(lifecycle, 'database_size_mb', lambda port, db: 120)
    monkeypatch.setattr(lifecycle, 'exec_in_container',
                        lambda container, cmd: (calls.append(('exec', container, cmd)) or (0, iter([b'loading...\n', b'done\n']))))
    return calls


# ── pre-update snapshot ────────────────────────────────────────────────────
def test_snapshot_is_named_pre_update_and_kept_next_to_backups(fakes, tmp_path):
    path = lifecycle.snapshot_before_update('alpha', 15432, 'db1', str(tmp_path))
    assert os.path.basename(path).startswith('pre-update-db1-') and os.path.exists(path)
    assert not os.path.exists(tmp_path / 'db1-20261015-120000.dump')      # renamed, not duplicated


def test_snapshot_retention_keeps_only_the_newest_three(fakes, tmp_path):
    for i in range(5):
        p = tmp_path / f'pre-update-db1-2026100{i}-000000.dump'
        p.write_text('old')
        os.utime(p, (1000 + i, 1000 + i))
    lifecycle.snapshot_before_update('alpha', 15432, 'db1', str(tmp_path), keep=3)
    remaining = sorted(f for f in os.listdir(tmp_path) if f.startswith('pre-update-db1-'))
    assert len(remaining) == 3


def test_snapshot_does_not_touch_other_databases_files(fakes, tmp_path):
    other = tmp_path / 'pre-update-db2-20260101-000000.dump'
    other.write_text('keep me')
    lifecycle.snapshot_before_update('alpha', 15432, 'db1', str(tmp_path), keep=1)
    assert other.exists()


def test_big_databases_are_not_snapshotted_automatically(fakes, monkeypatch, tmp_path):
    monkeypatch.setattr(lifecycle, 'database_size_mb', lambda port, db: 5000)
    assert lifecycle.snapshot_before_update('alpha', 15432, 'db1', str(tmp_path), max_mb=500) is None
    assert ('backup', 'db1') not in fakes


# ── module update ──────────────────────────────────────────────────────────
def test_module_update_snapshots_first_then_runs_odoo_with_the_real_conf(fakes, tmp_path):
    lines = []
    code = lifecycle.run_module_update('alpha', 15432, 'db1', 'sale', lines.append, str(tmp_path))
    assert code == 0
    steps = [c[0] for c in fakes]
    assert steps == ['backup', 'exec']                                   # snapshot BEFORE the update
    cmd = fakes[1][2]
    assert isinstance(cmd, list)                                         # no shell string
    assert cmd[:3] == ['odoo', '-c', '/etc/odoo/odoo.conf']
    assert '/tmp/odoo-runtime.conf' not in cmd
    assert cmd[cmd.index('-d') + 1] == 'db1' and cmd[cmd.index('-u') + 1] == 'sale'
    assert '--stop-after-init' in cmd and '--no-http' in cmd
    assert any('snapshot' in l.lower() for l in lines)
    assert 'loading...' in lines


def test_module_update_aborts_if_the_snapshot_fails(fakes, monkeypatch, tmp_path):
    def boom(port, db, directory):
        raise RuntimeError('disk full')
    monkeypatch.setattr(lifecycle, 'backup_database', boom)
    lines = []
    code = lifecycle.run_module_update('alpha', 15432, 'db1', 'sale', lines.append, str(tmp_path))
    assert code != 0
    assert not any(c[0] == 'exec' for c in fakes)
    assert any('aborted' in l.lower() for l in lines)


def test_module_update_can_skip_the_snapshot_explicitly(fakes, tmp_path):
    lifecycle.run_module_update('alpha', 15432, 'db1', 'sale', lambda l: None, str(tmp_path), snapshot=False)
    assert [c[0] for c in fakes] == ['exec']


@pytest.mark.parametrize('module', ['sale;rm -rf /', 'a b', '$(id)', '', '../x'])
def test_module_update_refuses_unsafe_arguments(fakes, tmp_path, module):
    code = lifecycle.run_module_update('alpha', 15432, 'db1', module, lambda l: None, str(tmp_path))
    assert code != 0 and fakes == []


# ── restore test ───────────────────────────────────────────────────────────
class RTConn:
    def __init__(self, log, results):
        self.log, self.results, self.autocommit = log, results, False

    def cursor(self):
        return self

    def execute(self, q, params=None):
        self.log.append(_render(q))

    def fetchone(self):
        return self.results.pop(0) if self.results else (0,)

    def close(self):
        pass


@pytest.fixture
def rt(monkeypatch, tmp_path):
    state = {'sql': [], 'pg_restore_rc': 0, 'results': [(42,), (1,)]}
    monkeypatch.setattr(lifecycle, '_connect', lambda port, dbname='postgres': RTConn(state['sql'], state['results']))
    monkeypatch.setattr(lifecycle.subprocess, 'run',
                        lambda *a, **k: type('R', (), {'returncode': state['pg_restore_rc'], 'stderr': 'pg_restore: error: connection to server at "db" failed: boom', 'stdout': ''})())
    d = tmp_path / 'backups'
    d.mkdir()
    (d / 'db1-20261015-120000.dump').write_text('x')
    state['dir'] = str(d)
    return state


def test_restore_check_restores_to_a_scratch_database_checks_and_drops_it(rt):
    result = lifecycle.restore_check('alpha', 15432, os.path.join(rt['dir'], 'db1-20261015-120000.dump'), rt['dir'])
    assert result['ok'] is True and result['checks']['users'] == 42
    sql = ' '.join(rt['sql'])
    assert 'CREATE DATABASE "zz-restore-test-' in sql
    assert 'DROP DATABASE IF EXISTS "zz-restore-test-' in sql
    assert sql.index('CREATE DATABASE') < sql.index('DROP DATABASE IF EXISTS')


def test_scratch_database_is_dropped_even_when_the_restore_fails(rt):
    rt['pg_restore_rc'] = 1
    result = lifecycle.restore_check('alpha', 15432, os.path.join(rt['dir'], 'db1-20261015-120000.dump'), rt['dir'])
    assert result['ok'] is False and 'boom' in result['error']
    assert 'DROP DATABASE IF EXISTS "zz-restore-test-' in ' '.join(rt['sql'])


def test_restore_check_never_touches_a_real_database_name(rt):
    lifecycle.restore_check('alpha', 15432, os.path.join(rt['dir'], 'db1-20261015-120000.dump'), rt['dir'])
    names = [s for s in rt['sql'] if 'DATABASE' in s]
    assert names and all('zz-restore-test-' in s for s in names)
    assert not any('"db1"' in s for s in rt['sql'])


def test_restore_check_refuses_paths_outside_the_backup_directory(rt, tmp_path):
    outside = tmp_path / 'secret.dump'
    outside.write_text('x')
    with pytest.raises(ValueError):
        lifecycle.restore_check('alpha', 15432, str(outside), rt['dir'])
    with pytest.raises(ValueError):
        lifecycle.restore_check('alpha', 15432, rt['dir'] + '/../secret.dump', rt['dir'])


def test_latest_backup_for_a_project_is_chosen_by_mtime(tmp_path):
    for i, name in enumerate(['a-1.dump', 'b-2.dump', 'pre-update-a-3.dump']):
        p = tmp_path / name
        p.write_text('x')
        os.utime(p, (100 + i, 100 + i))
    assert os.path.basename(lifecycle.latest_backup(str(tmp_path))) == 'b-2.dump'      # snapshots are not "backups"
    assert lifecycle.latest_backup(str(tmp_path / 'nope')) is None


# ── scheduled restore tests ────────────────────────────────────────────────
def test_run_restore_tests_checks_the_latest_backup_of_every_project(tmp_path, monkeypatch):
    for project in ('alpha', 'beta'):
        d = tmp_path / project
        d.mkdir()
    (tmp_path / 'alpha' / 'db1-1.dump').write_text('x')           # beta has no backup at all
    seen = []
    monkeypatch.setattr(lifecycle, 'restore_check',
                        lambda project, port, path, directory: seen.append((project, os.path.basename(path))) or
                        {'ok': True, 'checks': {'users': 3, 'modules': 5}, 'seconds': 1.0, 'error': ''})
    recorded = []
    results = lifecycle.run_restore_tests(
        [{'name': 'alpha', 'db_port': '1'}, {'name': 'beta', 'db_port': '2'}], str(tmp_path),
        record=lambda project, result: recorded.append((project, result['ok'])))
    assert seen == [('alpha', 'db1-1.dump')]
    assert {r['project']: r['status'] for r in results} == {'alpha': 'ok', 'beta': 'no-backup'}
    assert recorded == [('alpha', True)]


def test_one_failing_project_does_not_stop_the_others(tmp_path, monkeypatch):
    for project in ('alpha', 'beta'):
        (tmp_path / project).mkdir()
        (tmp_path / project / 'db-1.dump').write_text('x')

    def check(project, port, path, directory):
        if project == 'alpha':
            raise RuntimeError('pg_restore crashed')
        return {'ok': True, 'checks': {}, 'seconds': 0.1, 'error': ''}
    monkeypatch.setattr(lifecycle, 'restore_check', check)
    results = lifecycle.run_restore_tests(
        [{'name': 'alpha', 'db_port': '1'}, {'name': 'beta', 'db_port': '2'}], str(tmp_path), record=lambda p, r: None)
    assert {r['project']: r['status'] for r in results} == {'alpha': 'failed', 'beta': 'ok'}


def test_ignorable_pg_restore_errors_do_not_fail_the_test_when_the_data_is_there(rt):
    rt['pg_restore_rc'] = 1
    rt['results'][:] = [(42,), (1,)]
    # a plain per-object error ("already exists") exits 1 but the data restored fine
    import services.lifecycle as lc
    lc.subprocess.run = lambda *a, **k: type('R', (), {'returncode': 1, 'stderr': 'pg_restore: warning: errors ignored on restore: 2', 'stdout': ''})()
    result = lc.restore_check('alpha', 15432, os.path.join(rt['dir'], 'db1-20261015-120000.dump'), rt['dir'])
    assert result['ok'] is True


def test_an_empty_restore_is_a_failed_restore_test(rt):
    rt['results'][:] = [(0,), (0,)]
    result = lifecycle.restore_check('alpha', 15432, os.path.join(rt['dir'], 'db1-20261015-120000.dump'), rt['dir'])
    assert result['ok'] is False and 'empty' in result['error']
