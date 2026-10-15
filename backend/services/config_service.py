import configparser
import os
import re
from django.conf import settings


# Secrets are never sent to the browser: values of keys that look like secrets are
# replaced by MASK on read, and MASK sent back on write means "keep the stored value".
MASK = '********'
_SECRET_KEY = re.compile(r'(pass|secret|token|api_?key|private)', re.I)


def is_secret_key(key):
    return bool(_SECRET_KEY.search(str(key)))


def _mask(value, key):
    return MASK if value and is_secret_key(key) else value


def _project_dir(project_name, folder=None):
    """Resolve project directory. Uses folder from registry when available (e.g. projects/name)."""
    if folder:
        return os.path.join(settings.ODOO_DEV_BASE, folder)
    return os.path.join(settings.ODOO_DEV_BASE, 'projects', project_name)


def _conf_path(project_name, folder=None):
    base = _project_dir(project_name, folder)
    return os.path.join(base, 'config', 'odoo.conf')


def _find_odoo_conf(project_name, folder=None, conf_file=None):
    """Return path to odoo.conf. Uses explicit conf_file from registry when provided."""
    if conf_file:
        return os.path.join(settings.ODOO_DEV_BASE, conf_file)
    path = _conf_path(project_name, folder)
    if os.path.exists(path):
        return path
    # Fallback: flat structure at ODOO_DEV_BASE/project_name/config/odoo.conf
    flat = os.path.join(settings.ODOO_DEV_BASE, project_name, 'config', 'odoo.conf')
    if os.path.exists(flat):
        return flat
    return path  # Return primary path for error message


def _env_path(project_name, folder=None):
    # Look for .env in project root
    return os.path.join(_project_dir(project_name, folder), '.env')


def _find_env_path(project_name, folder=None):
    """Return path to .env, trying folder-based path first then flat project_name path."""
    path = _env_path(project_name, folder)
    if os.path.exists(path):
        return path
    flat = os.path.join(settings.ODOO_DEV_BASE, project_name, '.env')
    if os.path.exists(flat):
        return flat
    return path


def read_odoo_conf(project_name, folder=None, conf_file=None):
    path = _find_odoo_conf(project_name, folder, conf_file)
    if not os.path.exists(path):
        return {'error': f'odoo.conf not found at {path}'}
    cp = configparser.ConfigParser()
    cp.read(path)
    result = {}
    for section in cp.sections():
        result[section] = {k: _mask(v, k) for k, v in cp[section].items()}
    return result


def write_odoo_conf(project_name, data: dict, folder=None, conf_file=None):
    """data: {section: {key: value}}"""
    path = _find_odoo_conf(project_name, folder, conf_file)
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
    cp = configparser.ConfigParser()
    if os.path.exists(path):
        cp.read(path)
    for section, kv in data.items():
        if not cp.has_section(section):
            cp.add_section(section)
        for k, v in kv.items():
            if v == MASK:        # unchanged secret shown as a mask in the UI
                continue
            cp.set(section, k, str(v))
    with open(path, 'w') as f:
        cp.write(f)


def read_env_file(project_name, folder=None):
    path = _find_env_path(project_name, folder)
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
                key = k.strip()
                result[key] = _mask(v.strip().strip('"').strip("'"), key)
    return result


def write_env_file(project_name, data: dict, folder=None):
    path = _find_env_path(project_name, folder)
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
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
            if k in data and data[k] == MASK:
                new_lines.append(line)
                written_keys.add(k)
            elif k in data:
                new_lines.append(f'{k}={data[k]}\n')
                written_keys.add(k)
            else:
                new_lines.append(line)

    # Append new keys
    for k, v in data.items():
        if k not in written_keys and v != MASK:
            new_lines.append(f'{k}={v}\n')

    with open(path, 'w') as f:
        f.writelines(new_lines)
