import pytest

from services import db_service


@pytest.mark.parametrize('name', ['cnc', 'hr-base-17', 'Albadiya-Testing', 'a.b_c', 'x' * 63])
def test_valid_database_names(name):
    assert db_service._check_db_name(name) == name


@pytest.mark.parametrize('name', ['', 'a b', 'a;b', 'a"b', "a'b", '../etc', '-leading', 'x' * 64, 'db; DROP DATABASE x', None, 5])
def test_invalid_database_names_are_rejected(name):
    with pytest.raises(ValueError):
        db_service._check_db_name(name)


def test_project_password_reads_the_pgpass_file(odoo_base):
    secrets = odoo_base / 'secrets'
    secrets.mkdir()
    (secrets / 'alpha.pgpass').write_text('*:5432:*:odoo_app:p4ss\\:word\\\\x\n')
    assert db_service.project_password('alpha') == 'p4ss:word\\x'


def test_project_password_falls_back_to_the_legacy_shared_password(odoo_base, settings):
    assert db_service.project_password('does-not-exist') == settings.DB_PASSWORD
