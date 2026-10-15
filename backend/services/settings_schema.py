"""Curated runtime settings for a project's Odoo (the Odoo.sh-style subset).

The dashboard never exposes or edits the whole odoo.conf: only the keys below,
with types, ranges and cross-field / resource sanity checks. Writes happen only
through an approved ConfigChangeRequest (see apps/settings_app/views.py).
"""
import os
import re
import shutil
import time

import psutil
from django.conf import settings

MB = 1024 * 1024

# unit_factor: conf value = UI value * unit_factor
SCHEMA = {
    'workers': dict(label='HTTP workers', type='int', min=0, max=16, default=0, restart=True,
                    group='Capacity', help='Processes serving web requests. Each may use up to the hard memory limit. 0 = threaded mode (development only).'),
    'max_cron_threads': dict(label='Cron workers', type='int', min=0, max=4, default=2, restart=True,
                             group='Capacity', help='Parallel scheduled-action runners.'),
    'limit_memory_soft': dict(label='Memory soft limit (MB / worker)', type='int', min=256, max=8192, default=2048,
                              unit_factor=MB, restart=True, group='Limits', help='A worker above this is recycled after its current request.'),
    'limit_memory_hard': dict(label='Memory hard limit (MB / worker)', type='int', min=512, max=16384, default=2560,
                              unit_factor=MB, restart=True, group='Limits', help='A worker above this is killed immediately.'),
    'limit_time_cpu': dict(label='CPU time limit (s / request)', type='int', min=30, max=3600, default=60,
                           restart=True, group='Limits', help='Raise only for big imports/restores.'),
    'limit_time_real': dict(label='Request time limit (s)', type='int', min=60, max=7200, default=120,
                            restart=True, group='Limits', help='Wall-clock limit per request; must be at least the CPU limit.'),
    'limit_request': dict(label='Requests per worker before recycle', type='int', min=100, max=1000000, default=65536,
                          restart=True, group='Limits', help='Workers restart after this many requests.'),
    'db_maxconn': dict(label='Max DB connections per process', type='int', min=8, max=128, default=64,
                       restart=True, group='Limits', help='Keep (workers + cron) × this below the PostgreSQL max_connections.'),
    'log_level': dict(label='Log level', type='enum', default='info', restart=True, group='Logging',
                      choices=['critical', 'error', 'warn', 'info', 'debug', 'debug_rpc', 'debug_sql', 'test'],
                      help='debug levels are very verbose and slow; use temporarily.'),
}
SENSITIVE_LOG_LEVELS = {'debug_sql', 'debug_rpc', 'debug', 'test'}
_LINE = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$')


def conf_path(project):
    rel = project.get('conf_file') or f"{project['name']}/config/odoo.conf"
    return os.path.join(settings.ODOO_DEV_BASE, rel)


def _read_raw(path):
    values = {}
    if not os.path.exists(path):
        return values
    in_options = True
    with open(path) as f:
        for line in f:
            s = line.strip()
            if s.startswith('['):
                in_options = (s.lower() == '[options]')
                continue
            if not in_options or not s or s.startswith(('#', ';')):
                continue
            m = _LINE.match(line)
            if m:
                values[m.group(1)] = m.group(2)
    return values


def _to_ui(key, raw):
    spec = SCHEMA[key]
    if spec['type'] == 'enum':
        return raw
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value // spec.get('unit_factor', 1)


def current_values(project):
    """{key: {'value': ui_value, 'source': 'conf'|'default'}} for the curated keys."""
    raw = _read_raw(conf_path(project))
    out = {}
    for key, spec in SCHEMA.items():
        if key in raw:
            v = _to_ui(key, raw[key])
            out[key] = {'value': v if v is not None else spec['default'], 'source': 'conf'}
        else:
            out[key] = {'value': spec['default'], 'source': 'default'}
    return out


def host_resources():
    vm = psutil.virtual_memory()
    return {'cpu_count': psutil.cpu_count() or 1, 'ram_total_mb': vm.total // MB,
            'ram_available_mb': vm.available // MB}


def describe(project):
    cur = current_values(project)
    fields = []
    for key, spec in SCHEMA.items():
        fields.append({
            'key': key, 'label': spec['label'], 'type': spec['type'], 'group': spec['group'],
            'help': spec['help'], 'min': spec.get('min'), 'max': spec.get('max'),
            'choices': spec.get('choices'), 'default': spec['default'],
            'value': cur[key]['value'], 'source': cur[key]['source'], 'restart': spec['restart'],
        })
    return {'fields': fields, 'host': host_resources()}


def validate(project, requested):
    """Return (clean, errors, warnings). `clean` only holds keys that really change."""
    errors, warnings, clean = [], [], {}
    if not isinstance(requested, dict) or not requested:
        return {}, ['No changes submitted.'], []
    cur = current_values(project)
    for key, raw in requested.items():
        spec = SCHEMA.get(key)
        if not spec:
            errors.append(f'"{key}" is not a setting that can be changed here.')
            continue
        if spec['type'] == 'enum':
            if raw not in spec['choices']:
                errors.append(f'{spec["label"]}: must be one of {", ".join(spec["choices"])}.')
                continue
            value = raw
        else:
            try:
                value = int(str(raw).strip())
            except (TypeError, ValueError):
                errors.append(f'{spec["label"]}: "{raw}" is not a whole number.')
                continue
            if value < spec['min'] or value > spec['max']:
                errors.append(f'{spec["label"]}: must be between {spec["min"]} and {spec["max"]}.')
                continue
        if value != cur[key]['value']:
            clean[key] = value
    if errors:
        return {}, errors, warnings
    if not clean:
        return {}, ['Nothing would change: the submitted values equal the current ones.'], []

    merged = {k: v['value'] for k, v in cur.items()}
    merged.update(clean)
    host = host_resources()

    if merged['limit_memory_soft'] >= merged['limit_memory_hard']:
        errors.append('The memory soft limit must be lower than the hard limit.')
    if merged['limit_time_cpu'] > merged['limit_time_real']:
        errors.append('The CPU time limit cannot exceed the request time limit.')
    def _budget(vals, limit):
        procs = vals['workers'] + vals['max_cron_threads'] + (1 if vals['workers'] else 0)
        return procs * vals[limit], procs
    if any(k in clean for k in ('workers', 'max_cron_threads', 'limit_memory_soft', 'limit_memory_hard')) \
            and merged['workers']:
        cur_vals = {k: v['value'] for k, v in cur.items()}
        # soft limit = what a busy worker may realistically hold; hard = absolute ceiling
        new_soft, procs = _budget(merged, 'limit_memory_soft')
        old_soft, _ = _budget(cur_vals, 'limit_memory_soft')
        new_hard, _ = _budget(merged, 'limit_memory_hard')
        ram = host['ram_total_mb']
        if new_soft > old_soft and new_soft > ram * 2.5:
            errors.append(f'{procs} processes × {merged["limit_memory_soft"]} MB soft limit = {new_soft} MB, '
                          f'more than 2.5× this server\'s {ram} MB RAM. That cannot work.')
        elif new_soft > old_soft and new_soft > ram * 0.5:
            warnings.append(f'Memory budget grows to {new_soft} MB at the soft limit '
                            f'({new_hard} MB at the hard limit) on a {ram} MB server shared with every other '
                            f'project. Typical workers use far less, but a burst could starve neighbours or '
                            f'trigger the OOM killer.')
    if merged['workers'] > 2 * host['cpu_count'] + 1:
        warnings.append(f'{merged["workers"]} workers on a {host["cpu_count"]}-vCPU server will mostly wait for CPU; '
                        f'the usual maximum is {2 * host["cpu_count"] + 1}.')
    if merged['workers'] == 0 and 'workers' in clean:
        warnings.append('0 workers runs Odoo in threaded mode: no per-request limits and one process for web, '
                        'cron and long-polling. Use it only for development.')
    _procs = merged['workers'] + merged['max_cron_threads'] + (1 if merged['workers'] else 0)
    if merged['db_maxconn'] * max(_procs, 1) > 400:
        warnings.append('This many potential DB connections may exceed PostgreSQL max_connections (default 100).')
    if clean.get('log_level') in SENSITIVE_LOG_LEVELS:
        warnings.append(f'Log level "{clean["log_level"]}" is very verbose, slows Odoo and can write record data '
                        f'to the logs. Switch back when done.')
    if 'limit_time_real' in clean and clean['limit_time_real'] > 1200:
        warnings.append('Requests may run for more than 20 minutes; the proxy timeout in front of Odoo is 12 minutes.')
    return clean, errors, warnings


def restart_needed(changes):
    return any(SCHEMA[k]['restart'] for k in changes)


def backup_conf(project):
    path = conf_path(project)
    bdir = os.path.join(settings.DATA_DIR, 'conf-backups', project['name'])
    os.makedirs(bdir, exist_ok=True)
    dest = os.path.join(bdir, f"odoo.conf.{time.strftime('%Y%m%d-%H%M%S')}")
    shutil.copy2(path, dest)
    os.chmod(dest, 0o600)
    return dest


def restore_conf(project, backup_path):
    # in place (keeps the inode that the container bind-mounts)
    with open(backup_path) as src, open(conf_path(project), 'w') as dst:
        dst.write(src.read())


def write_values(project, changes):
    """Edit only the given keys, line by line; comments and everything else stay as they are."""
    path = conf_path(project)
    with open(path) as f:
        lines = f.read().splitlines(keepends=True)
    out, seen, in_options = [], set(), True
    insert_at = None
    for line in lines:
        s = line.strip()
        if s.startswith('['):
            in_options = (s.lower() == '[options]')
            if in_options:
                insert_at = len(out) + 1
            out.append(line)
            continue
        m = _LINE.match(line) if in_options and s and not s.startswith(('#', ';')) else None
        if m and m.group(1) in changes:
            key = m.group(1)
            spec = SCHEMA[key]
            out.append(f'{key} = {changes[key] * spec.get("unit_factor", 1) if spec["type"] == "int" else changes[key]}\n')
            seen.add(key)
        else:
            out.append(line)
    missing = [k for k in changes if k not in seen]
    if missing:
        add = [f'{k} = {changes[k] * SCHEMA[k].get("unit_factor", 1) if SCHEMA[k]["type"] == "int" else changes[k]}\n' for k in missing]
        pos = insert_at if insert_at is not None else len(out)
        out[pos:pos] = add
    with open(path, 'w') as f:
        f.writelines(out)
