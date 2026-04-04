import os
import subprocess
from django.conf import settings


def _git(path, *args, timeout=5):
    return subprocess.run(
        ['git', '-C', path] + list(args),
        capture_output=True, text=True, timeout=timeout,
    )


def _repo_path(folder):
    base = settings.ODOO_DEV_BASE
    return os.path.join(base, folder)


def get_git_info(folder):
    if not folder:
        return None, []
    path = _repo_path(folder)
    if not os.path.isdir(path):
        return None, []
    try:
        branch = _git(path, 'rev-parse', '--abbrev-ref', 'HEAD').stdout.strip()
        if not branch or branch == 'HEAD':
            return None, []
        local = _git(path, 'rev-parse', 'HEAD').stdout.strip()
        remote = _git(path, 'rev-parse', f'origin/{branch}')
        if remote.returncode != 0:
            return branch, []
        if local == remote.stdout.strip():
            return branch, []
        log = _git(path, 'log', f'HEAD..origin/{branch}', '--oneline').stdout.strip()
        pending = [ln for ln in log.splitlines() if ln]
        return branch, pending
    except Exception:
        return None, []


def get_commit_log(folder, n=20):
    if not folder:
        return []
    path = _repo_path(folder)
    if not os.path.isdir(path):
        return []
    try:
        result = _git(path, 'log', f'-{n}', '--pretty=format:%H|%s|%an|%ar')
        commits = []
        for line in result.stdout.splitlines():
            if not line:
                continue
            parts = line.split('|', 3)
            if len(parts) == 4:
                commits.append({
                    'hash': parts[0][:8],
                    'subject': parts[1],
                    'author': parts[2],
                    'date': parts[3],
                })
        return commits
    except Exception:
        return []


def get_current_commit(folder):
    if not folder:
        return None
    path = _repo_path(folder)
    try:
        result = _git(path, 'rev-parse', '--short', 'HEAD', timeout=3)
        return result.stdout.strip() or None
    except Exception:
        return None


def _find_compose_path_for_project(odoo_dev_base, folder=None, version=None):
    """Locate docker-compose.yml for a project (same logic as db_service._find_compose_path)."""
    if folder:
        candidate = os.path.join(odoo_dev_base, folder)
        while candidate and candidate != odoo_dev_base and candidate != '/':
            compose = os.path.join(candidate, 'docker-compose.yml')
            if os.path.exists(compose):
                return compose
            candidate = os.path.dirname(candidate)
    if version:
        versioned = os.path.join(odoo_dev_base, f'v{version}', 'docker-compose.yml')
        if os.path.exists(versioned):
            return versioned
    return None


def _build_host_to_container_map(compose_path):
    """
    Parse a docker-compose.yml and return a dict mapping host paths to container
    paths for all /mnt/* volume mounts.  Expands $HOME / ${HOME}.
    """
    if not compose_path or not os.path.exists(compose_path):
        return {}
    import re as _re
    host_home = os.path.dirname(settings.ODOO_DEV_BASE)
    with open(compose_path) as fh:
        content = fh.read()
    content = content.replace('${HOME}', host_home).replace('$HOME', host_home)
    content = content.replace('${ODOO_DEV_BASE}', settings.ODOO_DEV_BASE)
    result = {}
    for m in _re.finditer(r'^\s*-\s+([^:]+):(/mnt/[^:\s]+)', content, _re.MULTILINE):
        host = m.group(1).strip()
        container = m.group(2).strip()
        result[host] = container
    return result


def get_addons_path(project_name, folder=None, version=None):
    """
    Auto-detect addon paths by scanning the project directory for __manifest__.py files.
    Uses the same logic as entrypoint-wrapper.sh: every unique parent directory that
    contains at least one Odoo module becomes an addons_path entry.

    folder:  registry folder field (e.g. 'projects/medtech' or 'projects/pac/repo'
             or 'worktrees/hr-base-17')
    version: odoo version string (e.g. '17') used to locate the docker-compose.yml
             when the folder is inside a worktree rather than a project directory.
    """
    base = settings.ODOO_DEV_BASE
    addons_dir = os.path.join(base, folder) if folder else os.path.join(base, 'projects', project_name)

    if not os.path.isdir(addons_dir):
        return []

    # Try to find the docker-compose.yml so we can map host paths → container paths
    compose_path = _find_compose_path_for_project(base, folder=folder, version=version)
    host_to_container = _build_host_to_container_map(compose_path)

    def _host_to_container_path(host_path):
        """Reverse-map a host path to its container /mnt/... path."""
        if host_path in host_to_container:
            return host_to_container[host_path]
        for h, c in host_to_container.items():
            if host_path.startswith(h + '/'):
                return c + host_path[len(h):]
        return None

    # Determine which host directories to scan.
    # When a compose file is available, scan ALL non-enterprise /mnt/* source dirs
    # (covers cases like odoo17 where hr-base and project addons are separate mounts).
    # Fall back to just the registry folder when no compose is found.
    _SKIP_CONTAINERS = {'/mnt/enterprise-addons'}
    _SKIP_DIRS = {'.git', '__pycache__', '.idea', 'node_modules', 'static'}

    if host_to_container:
        scan_dirs = [
            h for h, c in host_to_container.items()
            if c not in _SKIP_CONTAINERS and os.path.isdir(h)
        ]
    else:
        scan_dirs = [addons_dir]

    # Walk each source dir, collect every parent dir that contains __manifest__.py
    parent_dirs = set()
    for scan_root in scan_dirs:
        for root, dirs, files in os.walk(scan_root):
            dirs[:] = [d for d in dirs if d not in _SKIP_DIRS and not d.startswith('.')]
            if '__manifest__.py' in files:
                parent_dirs.add(os.path.dirname(root))

    if not parent_dirs:
        return []

    # Build entries: fixed headers first, then sorted project paths
    entries = [
        {'path': '/usr/lib/python3/dist-packages/odoo/addons', 'label': 'Odoo Core',   'kind': 'core'},
        {'path': '/mnt/enterprise-addons',                      'label': 'Enterprise',  'kind': 'enterprise'},
    ]

    # Sort: scan_dir roots first (by container path), then subdirs alphabetically
    scan_dirs_set = set(scan_dirs)
    for host_path in sorted(parent_dirs, key=lambda p: (p not in scan_dirs_set, p)):
        # Try compose-based reverse mapping first
        container_path = _host_to_container_path(host_path)
        if not container_path:
            # Fall back to /mnt/project-addons convention
            if host_path == addons_dir:
                container_path = '/mnt/project-addons'
            else:
                rel = os.path.relpath(host_path, addons_dir)
                container_path = f'/mnt/project-addons/{rel}'
        kind, label = _classify_path(container_path)
        entries.append({'path': container_path, 'label': label, 'kind': kind})

    return entries


def _classify_path(p):
    lp = p.lower()
    if 'enterprise' in lp:
        return 'enterprise', 'Enterprise'
    if lp.startswith('/usr/') or 'dist-packages' in lp or 'site-packages' in lp:
        return 'core', 'Odoo Core'
    # /mnt/extra-addons (root) → HR Base
    if p == '/mnt/extra-addons' or p.endswith('/extra-addons'):
        return 'extra', 'HR Base'
    # /mnt/extra-addons/<sub> → HR Base / <sub>
    if p.startswith('/mnt/extra-addons/'):
        sub = p[len('/mnt/extra-addons/'):].split('/')[0]
        return 'extra', f'HR Base / {sub}'
    # /mnt/hr-base-addons (root) → HR Base
    if p == '/mnt/hr-base-addons' or p.endswith('/hr-base-addons'):
        return 'extra', 'HR Base'
    # /mnt/hr-base-addons/<sub> → HR Base / <sub>
    if p.startswith('/mnt/hr-base-addons/'):
        sub = p[len('/mnt/hr-base-addons/'):].split('/')[0]
        return 'extra', f'HR Base / {sub}'
    if 'extra' in lp and 'addons' in lp:
        return 'extra', 'Extra Addons'
    if p == '/mnt/project-addons' or p.endswith('/project-addons'):
        return 'project', 'Project Root'
    if '/project-addons/' in p:
        sub = p.rsplit('/', 1)[-1]
        return 'project-sub', f'Project / {sub}'
    label = p.rsplit('/', 1)[-1] or p
    return 'other', label


def git_pull(folder, output_queue):
    path = _repo_path(folder)
    try:
        proc = subprocess.Popen(
            ['git', '-C', path, 'pull', '--ff-only'],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        for line in proc.stdout:
            output_queue.put(line.rstrip())
        proc.wait()
        output_queue.put(f'--- exit code: {proc.returncode} ---')
    except Exception as e:
        output_queue.put(f'Error: {e}')
    finally:
        output_queue.put(None)


# Branch management

def get_branches_quick(folder):
    """Return all known branches (local + remote-tracked) without doing a network fetch."""
    path = _repo_path(folder)
    if not os.path.isdir(path):
        return []
    try:
        local_out = _git(path, 'branch', '--format=%(refname:short)', timeout=3).stdout.strip()
        remote_out = _git(path, 'branch', '-r', '--format=%(refname:short)', timeout=3).stdout.strip()
        local = [b for b in local_out.splitlines() if b]
        remote = [b.replace('origin/', '') for b in remote_out.splitlines() if b and 'HEAD' not in b]
        return sorted(set(local + remote))
    except Exception:
        return []


def list_branches(folder):
    path = _repo_path(folder)
    if not os.path.isdir(path):
        return {'local': [], 'remote': [], 'current': None}
    try:
        # Fetch to get up-to-date remotes
        _git(path, 'fetch', '--all', timeout=30)
        current = _git(path, 'rev-parse', '--abbrev-ref', 'HEAD').stdout.strip()
        local_out = _git(path, 'branch', '--format=%(refname:short)').stdout.strip()
        remote_out = _git(path, 'branch', '-r', '--format=%(refname:short)').stdout.strip()
        local = [b for b in local_out.splitlines() if b]
        remote = [b for b in remote_out.splitlines() if b and 'HEAD' not in b]
        return {'local': local, 'remote': remote, 'current': current}
    except Exception as e:
        return {'error': str(e)}


def switch_branch(folder, branch, output_queue):
    path = _repo_path(folder)
    try:
        # Try local checkout first, then track remote
        result = _git(path, 'checkout', branch, timeout=30)
        if result.returncode != 0:
            # Try tracking remote branch
            result = _git(path, 'checkout', '-b', branch, f'origin/{branch}', timeout=30)
        output = (result.stdout + result.stderr).strip()
        for line in output.splitlines():
            output_queue.put(line)
        output_queue.put(f'--- exit code: {result.returncode} ---')
    except Exception as e:
        output_queue.put(f'Error: {e}')
    finally:
        output_queue.put(None)


def get_submodule_status(folder):
    path = _repo_path(folder)
    if not os.path.isdir(path):
        return []
    try:
        result = _git(path, 'submodule', 'status', '--recursive', timeout=15)
        submodules = []
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            # Format: [+- ]hash path (branch)
            status_char = line[0]
            rest = line[1:].strip()
            parts = rest.split(' ', 2)
            commit = parts[0] if parts else ''
            sub_path = parts[1] if len(parts) > 1 else ''
            status = 'modified' if status_char == '+' else 'behind' if status_char == '-' else 'clean'
            submodules.append({'path': sub_path, 'commit': commit[:8], 'status': status})
        return submodules
    except Exception:
        return []


def update_submodules(folder, output_queue):
    path = _repo_path(folder)
    try:
        proc = subprocess.Popen(
            ['git', '-C', path, 'submodule', 'update', '--init', '--recursive', '--remote'],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        for line in proc.stdout:
            output_queue.put(line.rstrip())
        proc.wait()
        output_queue.put(f'--- exit code: {proc.returncode} ---')
    except Exception as e:
        output_queue.put(f'Error: {e}')
    finally:
        output_queue.put(None)
