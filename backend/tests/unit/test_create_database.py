import pytest

from services import db_service


@pytest.fixture
def fakes(monkeypatch):
    calls = []
    monkeypatch.setattr(db_service, 'list_database_names', lambda port: ['existing'])
    monkeypatch.setattr(db_service, 'exec_in_container_sync',
                        lambda container, cmd: (calls.append(('init', container, list(cmd))) or (0, b'')))
    monkeypatch.setattr(db_service, 'neutralize_database',
                        lambda project, dbname, db_port=None: calls.append(('neutralize', project, dbname)))
    monkeypatch.setattr(db_service, 'lock_down_database', lambda port, dbname: calls.append(('lock', dbname)))
    monkeypatch.setattr(db_service, 'set_odoo_user_password',
                        lambda project, port, dbname, login='admin': calls.append(('password', dbname, login)) or 'pw')
    return calls


def test_new_database_is_initialised_neutralized_and_gets_an_individual_password(fakes):
    login, password = db_service.create_odoo_database('alpha', 15432, 'scratch')
    assert (login, password) == ('admin', 'pw')
    steps = [c[0] for c in fakes]
    # order matters: initialise, neutralize, lock down, then set the password
    assert steps == ['init', 'neutralize', 'lock', 'password']
    assert fakes[1][1:] == ('alpha', 'scratch')


def test_demo_data_is_off_by_default(fakes):
    db_service.create_odoo_database('alpha', 15432, 'scratch')
    assert '--without-demo=all' in fakes[0][2]


def test_existing_database_is_not_overwritten(fakes):
    with pytest.raises(ValueError):
        db_service.create_odoo_database('alpha', 15432, 'existing')
    assert fakes == []


def test_init_runs_without_binding_the_servers_ports(fakes):
    """The init process runs next to the live server inside the same container: it must not
    try to bind the HTTP/longpolling port ('Address already in use') or start workers."""
    db_service.create_odoo_database('alpha', 15432, 'scratch')
    cmd = fakes[0][2]
    assert '--no-http' in cmd and '--stop-after-init' in cmd
    assert '--workers=0' in cmd and '--max-cron-threads=0' in cmd
    assert cmd[:3] == ['odoo', '-c', '/etc/odoo/odoo.conf']
