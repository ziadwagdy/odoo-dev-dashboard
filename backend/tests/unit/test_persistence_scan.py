"""Detect persistence planted inside Odoo databases (the 2026 incident's server actions).
Written first (Phase 4b)."""
import pytest

from apps.security.models import SecurityAlert, SeenItem
from services import persistence_scan as ps
from services.alerting import AlertManager

pytestmark = pytest.mark.django_db


class FakeOdoo:
    """Stands in for the databases: {(project, db): {kind: [(id, label), ...]}}"""
    def __init__(self):
        self.data = {}

    def fetch(self, project, db, kind):
        return list(self.data.get((project, db), {}).get(kind, []))


@pytest.fixture
def env():
    odoo = FakeOdoo()
    seen_alerts = []

    class Rec:
        def notify(self, alert, kind):
            seen_alerts.append((alert.severity, kind, alert.summary))
    manager = AlertManager(notifiers=[Rec()])
    return odoo, manager, seen_alerts


def scan(odoo, manager):
    return ps.run_scan([{'name': 'alpha', 'db_port': '1'}], lambda port: ['db1'], odoo.fetch, manager.handle)


def test_the_first_scan_only_records_a_baseline_and_raises_nothing(env):
    odoo, manager, alerts = env
    odoo.data[('alpha', 'db1')] = {'code_action': [(10, 'Existing action')], 'system_user': [(2, 'admin')]}
    scan(odoo, manager)
    assert SecurityAlert.objects.count() == 0 and alerts == []
    assert SeenItem.objects.filter(scope='alpha:db1').count() == 2


def test_a_new_server_action_with_code_after_the_baseline_alerts_high(env):
    odoo, manager, alerts = env
    scan(odoo, manager)                                          # baseline (empty)
    odoo.data[('alpha', 'db1')] = {'code_action': [(5692, '_ffd0007e486a2825_')]}
    scan(odoo, manager)
    a = SecurityAlert.objects.get()
    assert a.rule == 'odoo_persistence' and a.severity == 'high' and a.status == 'open'
    assert 'server action' in a.summary.lower() and 'db1' in a.summary and '_ffd0007e486a2825_' in a.summary
    assert alerts and alerts[0][1] == 'new'


def test_each_kind_is_detected(env):
    odoo, manager, _ = env
    scan(odoo, manager)
    odoo.data[('alpha', 'db1')] = {
        'code_action': [(1, 'a')], 'system_user': [(9, 'mallory')], 'api_key': [(3, 'key')], 'python_cron': [(4, 'c')]}
    scan(odoo, manager)
    summaries = ' | '.join(SecurityAlert.objects.values_list('summary', flat=True)).lower()
    for word in ('server action', 'administrator', 'api key', 'scheduled action'):
        assert word in summaries


def test_an_item_alerts_only_once(env):
    odoo, manager, _ = env
    scan(odoo, manager)
    odoo.data[('alpha', 'db1')] = {'system_user': [(9, 'mallory')]}
    scan(odoo, manager)
    scan(odoo, manager)
    scan(odoo, manager)
    assert SecurityAlert.objects.count() == 1 and SecurityAlert.objects.get().count == 1


def test_a_removed_and_re_added_item_is_not_re_announced_unless_it_is_new(env):
    odoo, manager, _ = env
    odoo.data[('alpha', 'db1')] = {'system_user': [(2, 'admin')]}
    scan(odoo, manager)
    odoo.data[('alpha', 'db1')] = {'system_user': [(2, 'admin'), (9, 'mallory')]}
    scan(odoo, manager)
    assert SecurityAlert.objects.count() == 1


def test_a_new_database_gets_its_own_silent_baseline(env):
    odoo, manager, _ = env
    scan(odoo, manager)
    odoo.data[('alpha', 'db2')] = {'code_action': [(1, 'legit-but-new-db')]}
    ps.run_scan([{'name': 'alpha', 'db_port': '1'}], lambda port: ['db1', 'db2'], odoo.fetch, manager.handle)
    assert SecurityAlert.objects.count() == 0


def test_an_unreadable_database_is_skipped_not_fatal(env):
    odoo, manager, _ = env

    def fetch(project, db, kind):
        if db == 'bad':
            raise RuntimeError('permission denied')
        return odoo.fetch(project, db, kind)
    ps.run_scan([{'name': 'alpha', 'db_port': '1'}], lambda port: ['bad', 'db1'], fetch, manager.handle)
    assert SeenItem.objects.filter(scope='alpha:db1').count() == 0       # empty baseline recorded for db1 is fine
    # the important part: no exception escaped


def test_the_server_action_query_ignores_actions_shipped_by_modules_and_never_reads_code():
    q = ps.QUERIES['code_action']
    assert "state = 'code'" in q and 'ir_model_data' in q
    assert 'code' not in q.replace("state = 'code'", '').lower().split('select', 1)[1].split('from')[0]   # no code column selected
