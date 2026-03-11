import os
from django.conf import settings


def read_registry():
    registry_file = settings.REGISTRY_FILE
    projects = []
    if not os.path.exists(registry_file):
        return projects
    with open(registry_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split('|')
            if len(parts) >= 5:
                projects.append({
                    'name':      parts[0],
                    'version':   parts[1],
                    'odoo_port': parts[2],
                    'db_port':   parts[3],
                    'url':       parts[4],
                    'container': f'{parts[0]}-app',
                    'folder':    parts[5].strip() if len(parts) >= 6 else None,
                })
    return projects


def get_project(name):
    for p in read_registry():
        if p['name'] == name:
            return p
    return None
