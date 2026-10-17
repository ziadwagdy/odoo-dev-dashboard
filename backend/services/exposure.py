"""What the dashboard may reveal about a project.

The registry line carries operational details (ports, host folders, config paths) that no
dashboard user needs: they never connect to those ports, and paths help only an attacker.
Everything the UI shows goes through public_project().
"""
import re

_HR_BASE = re.compile(r'hr[-_]base', re.I)


def public_project(p):
    return {
        'name': p['name'],
        'version': p.get('version'),
        'url': p.get('url'),
        'container': p.get('container'),
        'uses_hr_base': bool(_HR_BASE.search(p.get('folder') or '')),
    }
