import configparser
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


def get_addons_path(project_name):
    base = settings.ODOO_DEV_BASE
    conf_path = os.path.join(base, project_name, 'config', 'odoo.conf')
    if not os.path.exists(conf_path):
        return []
    cp = configparser.ConfigParser()
    cp.read(conf_path)
    raw = cp.get('options', 'addons_path', fallback='')
    if not raw:
        return []
    entries = []
    for p in raw.split(','):
        p = p.strip()
        if not p:
            continue
        kind, label = _classify_path(p)
        entries.append({'path': p, 'label': label, 'kind': kind})
    return entries


def _classify_path(p):
    lp = p.lower()
    if 'enterprise' in lp:
        return 'enterprise', 'Enterprise'
    if 'extra' in lp and 'addons' in lp:
        return 'extra', 'Extra Addons'
    if lp.startswith('/usr/') or 'dist-packages' in lp or 'site-packages' in lp:
        return 'core', 'Odoo Core'
    if p == '/mnt/project-addons' or p.endswith('/project-addons'):
        return 'project', 'Project Root'
    if '/project-addons/' in p or '/mnt/project-addons/' in p:
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
