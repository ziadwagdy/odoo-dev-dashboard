import configparser
import os
from django.conf import settings


def _conf_path(project_name):
    return os.path.join(settings.ODOO_DEV_BASE, project_name, 'config', 'odoo.conf')


def _env_path(project_name):
    # Look for .env in project root
    return os.path.join(settings.ODOO_DEV_BASE, project_name, '.env')


def read_odoo_conf(project_name):
    path = _conf_path(project_name)
    if not os.path.exists(path):
        return {'error': f'odoo.conf not found at {path}'}
    cp = configparser.ConfigParser()
    cp.read(path)
    result = {}
    for section in cp.sections():
        result[section] = dict(cp[section])
    return result


def write_odoo_conf(project_name, data: dict):
    """data: {section: {key: value}}"""
    path = _conf_path(project_name)
    cp = configparser.ConfigParser()
    if os.path.exists(path):
        cp.read(path)
    for section, kv in data.items():
        if not cp.has_section(section):
            cp.add_section(section)
        for k, v in kv.items():
            cp.set(section, k, str(v))
    with open(path, 'w') as f:
        cp.write(f)


def read_env_file(project_name):
    path = _env_path(project_name)
    if not os.path.exists(path):
        return {}
    result = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k, _, v = line.partition('=')
                result[k.strip()] = v.strip().strip('"').strip("'")
    return result


def write_env_file(project_name, data: dict):
    path = _env_path(project_name)
    # Preserve comments from existing file
    existing_lines = []
    if os.path.exists(path):
        with open(path) as f:
            existing_lines = f.readlines()

    written_keys = set()
    new_lines = []
    for line in existing_lines:
        stripped = line.strip()
        if stripped.startswith('#') or not stripped:
            new_lines.append(line)
            continue
        if '=' in stripped:
            k = stripped.partition('=')[0].strip()
            if k in data:
                new_lines.append(f'{k}={data[k]}\n')
                written_keys.add(k)
            else:
                new_lines.append(line)

    # Append new keys
    for k, v in data.items():
        if k not in written_keys:
            new_lines.append(f'{k}={v}\n')

    with open(path, 'w') as f:
        f.writelines(new_lines)
