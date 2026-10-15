import os

import pytest

from services import settings_schema as S

PROJECT = {'name': 'alpha', 'conf_file': 'alpha/config/odoo.conf'}


@pytest.fixture(autouse=True)
def _host(monkeypatch):
    # fixed, small host so the memory rules are deterministic
    monkeypatch.setattr(S, 'host_resources', lambda: {'cpu_count': 2, 'ram_total_mb': 8000, 'ram_available_mb': 4000})


def test_current_values_read_from_conf_and_converted_to_mb(odoo_base):
    cur = S.current_values(PROJECT)
    assert cur['workers'] == {'value': 2, 'source': 'conf'}
    assert cur['limit_memory_soft']['value'] == 2048          # bytes in the file, MB in the UI
    assert cur['limit_memory_hard']['value'] == 2560
    assert cur['limit_request'] == {'value': 65536, 'source': 'default'}


@pytest.mark.parametrize('key', ['addons_path', 'admin_passwd', 'db_password', 'db_host', 'list_db', 'proxy_mode'])
def test_keys_outside_the_allow_list_are_rejected(odoo_base, key):
    clean, errors, _ = S.validate(PROJECT, {key: 'x'})
    assert clean == {} and errors and 'not a setting that can be changed' in errors[0]


def test_rejects_non_numbers_and_out_of_range(odoo_base):
    assert S.validate(PROJECT, {'workers': 'many'})[1]
    assert S.validate(PROJECT, {'workers': 99})[1]
    assert S.validate(PROJECT, {'workers': -1})[1]
    assert S.validate(PROJECT, {'limit_time_cpu': 5})[1]


def test_no_change_is_an_error(odoo_base):
    _, errors, _ = S.validate(PROJECT, {'workers': 2})
    assert errors and 'Nothing would change' in errors[0]


def test_empty_request_is_an_error(odoo_base):
    assert S.validate(PROJECT, {})[1]
    assert S.validate(PROJECT, None)[1]


def test_soft_limit_must_be_below_hard_limit(odoo_base):
    _, errors, _ = S.validate(PROJECT, {'limit_memory_soft': 4096, 'limit_memory_hard': 2048})
    assert any('soft limit must be lower' in e for e in errors)


def test_cpu_limit_cannot_exceed_request_limit(odoo_base):
    _, errors, _ = S.validate(PROJECT, {'limit_time_cpu': 900, 'limit_time_real': 300})
    assert any('CPU time limit cannot exceed' in e for e in errors)


def test_log_level_is_an_enum_and_debug_levels_warn(odoo_base):
    assert S.validate(PROJECT, {'log_level': 'chatty'})[1]
    clean, errors, warnings = S.validate(PROJECT, {'log_level': 'debug_sql'})
    assert not errors and clean == {'log_level': 'debug_sql'}
    assert any('verbose' in w for w in warnings)


def test_changing_only_log_level_never_triggers_memory_rules(odoo_base):
    _, errors, warnings = S.validate(PROJECT, {'log_level': 'warn'})
    assert not errors and not warnings


def test_growing_the_memory_budget_warns_then_errors(odoo_base):
    _, errors, warnings = S.validate(PROJECT, {'workers': 4})
    assert not errors and any('Memory budget grows' in w for w in warnings)
    _, errors, _ = S.validate(PROJECT, {'workers': 16, 'limit_memory_soft': 8192, 'limit_memory_hard': 16384})
    assert any('cannot work' in e for e in errors)


def test_shrinking_resources_is_not_flagged(odoo_base):
    _, errors, warnings = S.validate(PROJECT, {'workers': 1})
    assert not errors and not any('Memory budget' in w for w in warnings)


def test_many_workers_on_few_cpus_warns(odoo_base):
    _, _, warnings = S.validate(PROJECT, {'workers': 8, 'limit_memory_soft': 512, 'limit_memory_hard': 1024})
    assert any('vCPU' in w for w in warnings)


def test_workers_zero_warns_about_threaded_mode(odoo_base):
    _, _, warnings = S.validate(PROJECT, {'workers': 0})
    assert any('threaded mode' in w for w in warnings)


def test_every_schema_key_requires_restart(odoo_base):
    assert S.restart_needed({'workers': 3}) is True


def test_write_values_changes_only_requested_keys_and_converts_units(odoo_base):
    path = S.conf_path(PROJECT)
    before = open(path).read()
    S.write_values(PROJECT, {'workers': 3, 'limit_memory_hard': 3072})
    after = open(path).read()
    assert 'workers = 3' in after
    assert f'limit_memory_hard = {3072 * 1024 * 1024}' in after
    # every other line is byte-for-byte what it was (secrets included)
    changed = {l for l in before.splitlines() if l not in after.splitlines()}
    assert {l.split(' = ')[0] for l in changed} == {'workers', 'limit_memory_hard'}


def test_write_values_appends_missing_keys_inside_options(odoo_base):
    S.write_values(PROJECT, {'limit_request': 1000})
    text = open(S.conf_path(PROJECT)).read()
    assert 'limit_request = 1000' in text
    assert text.index('[options]') < text.index('limit_request')


def test_backup_and_restore_roundtrip(odoo_base, settings):
    original = open(S.conf_path(PROJECT)).read()
    backup = S.backup_conf(PROJECT)
    assert oct(os.stat(backup).st_mode & 0o777) == '0o600'
    S.write_values(PROJECT, {'workers': 5})
    assert open(S.conf_path(PROJECT)).read() != original
    S.restore_conf(PROJECT, backup)
    assert open(S.conf_path(PROJECT)).read() == original
