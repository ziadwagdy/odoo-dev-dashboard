#!/usr/bin/env python3
"""Move every project to its own Postgres password, delivered as ~/.pgpass.

For each project:
  1. new random password for the project's `odoo_app` role (stored only in
     ~/odoo-dev/secrets/<project>.pgpass, owned by the container's odoo user, mode 600)
  2. odoo.conf loses `db_password`; the compose service loses HOST/USER/PASSWORD env and
     gets `entrypoint: ["odoo"]` + `command: ["-c", "/etc/odoo/odoo.conf"]` (the stock
     entrypoint would put --db_password on the command line) and the .pgpass bind mount
  3. the app container is recreated and verified (health, a DB-touching request, no auth
     failures, no password in the process arguments, dashboard can list the databases)
  4. on any failure the project is rolled back (old role password, old files, old container)

Usage:  python3 pgpass-rollout.py omc-holding            # one project
        python3 pgpass-rollout.py --all                  # every project, stops on first failure
        python3 pgpass-rollout.py --dry-run --all        # show the planned edits only
"""
import json, os, re, secrets, shutil, subprocess, sys, time, urllib.error, urllib.request

BASE = '/home/zeyad/odoo-dev'
BACKEND = 'odoo-dev-dashboard-backend-1'
BK = os.path.expanduser(f"~/security-evidence/pgpass-backup-{time.strftime('%Y%m%d-%H%M%S')}")

# name: (db container, app container, compose dir, compose service, conf path relative to BASE, host port)
PROJECTS = {
    'omc-holding': ('omc-holding-db', 'omc-holding-app', 'omc-holding', 'omc-holding-app', 'omc-holding/config/odoo.conf', 18191),
    'sivas':       ('sivas-db', 'sivas-app', 'sivas', 'sivas-app', 'sivas/config/odoo.conf', 8082),
    'albadiya':    ('albadiya-db', 'albadiya-app', 'albadiya', 'albadiya-app', 'albadiya/config/odoo.conf', 8072),
    'iba':         ('iba-db', 'iba-app', 'iba', 'iba-app', 'iba/config/odoo.conf', 8078),
    'medtechcorp': ('medtechcorp-db', 'medtechcorp-app', 'medtechcorp', 'medtechcorp-app', 'medtechcorp/config/odoo.conf', 8076),
    'vodafone':    ('vodafone-db', 'vodafone-app', 'vodafone', 'vodafone-app', 'vodafone/config/odoo.conf', 8079),
    'lexus-dev':   ('lexus-dev-db', 'lexus-dev-app', 'lexus-dev', 'lexus-dev-app', 'lexus-dev/config/odoo.conf', 8075),
    'odoo17':      ('odoo17-db', 'odoo17-app', 'v17', 'odoo17', 'v17/config/odoo.conf', 8069),
    'alif':        ('alif-db', 'alif-app', 'v17', 'alif', 'v17/config/alif.conf', 18171),
    'odoo18':      ('odoo18-db', 'odoo18-app', 'v18', 'odoo18', 'v18/config/odoo.conf', 8070),
    'pac-stage':   ('pac-stage-db', 'pac-stage-app', 'v18', 'pac-stage', 'v18/config/pac-stage.conf', 18181),
    'odoo19':      ('odoo19-db', 'odoo19-app', 'v19', 'odoo19', 'v19/config/odoo.conf', 8071),
}


def sh(*cmd, inp=None, check=True, cwd=None):
    r = subprocess.run(cmd, input=inp, capture_output=True, text=True, cwd=cwd)
    if check and r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd[:4])}…: {r.stderr.strip()[:300] or r.stdout.strip()[:300]}")
    return r.stdout


def backend_py(code, **env):
    args = ['docker', 'exec', '-i']
    for k, v in env.items():
        args += ['-e', f'{k}={v}']
    return sh(*args, BACKEND, 'python', '-', inp=code)


def admin_user(db):
    for u in ('odoo', 'pgroot'):
        r = subprocess.run(['docker', 'exec', db, 'psql', '-U', u, '-d', 'postgres', '-tAc',
                            'select rolsuper from pg_roles where rolname=current_user'], capture_output=True, text=True)
        if r.stdout.strip() == 't':
            return u
    raise RuntimeError(f'no superuser reachable in {db}')


def set_role_password(db, password):
    sh('docker', 'exec', '-i', db, 'psql', '-U', admin_user(db), '-d', 'postgres', '-v', 'ON_ERROR_STOP=1', '-q',
       '-v', f'pw={password}', inp="ALTER ROLE odoo_app PASSWORD :'pw';\n")


def patch_compose(text, service, app_container):
    lines = text.splitlines(keepends=True)
    # locate the service block
    start = next((i for i, l in enumerate(lines) if re.match(rf'^  {re.escape(service)}:\s*$', l)), None)
    if start is None:
        raise RuntimeError(f'service {service} not found in compose file')
    end = next((i for i in range(start + 1, len(lines)) if re.match(r'^  \S|^\S', lines[i])), len(lines))
    block = lines[start:end]
    if any(re.match(r'^\s+(command|entrypoint):', l) for l in block):
        raise RuntimeError('service already has command/entrypoint; refusing to guess')
    out, i = [], 0
    while i < len(block):
        l = block[i]
        if re.match(r'^\s+(-\s*)?(HOST|USER|PASSWORD)\s*[=:]', l):
            i += 1
            continue
        out.append(l)
        i += 1
    # drop an `environment:` header that is now empty
    cleaned = []
    for idx, l in enumerate(out):
        if re.match(r'^\s+environment:\s*$', l):
            nxt = out[idx + 1] if idx + 1 < len(out) else ''
            indent = len(l) - len(l.lstrip())
            if not nxt.strip() or (len(nxt) - len(nxt.lstrip())) <= indent:
                continue
        cleaned.append(l)
    out = cleaned
    # entrypoint/command after container_name
    idx = next(i for i, l in enumerate(out) if re.match(r'^\s+container_name:', l))
    ind = re.match(r'^(\s+)', out[idx]).group(1)
    out[idx + 1:idx + 1] = [f'{ind}entrypoint: ["odoo"]\n', f'{ind}command: ["-c", "/etc/odoo/odoo.conf"]\n']
    # pgpass mount after the dashboard-addons mount
    mount = f'{BASE}/secrets/{{name}}.pgpass:/var/lib/odoo/.pgpass:ro'
    j = next((i for i, l in enumerate(out) if ':/mnt/dashboard-addons' in l), None)
    if j is None:
        raise RuntimeError('dashboard-addons mount missing; run the addon rollout first')
    vind = re.match(r'^(\s+)', out[j]).group(1)
    out.insert(j + 1, f'{vind}- {mount}\n')
    return ''.join(lines[:start] + out + lines[end:])


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def http_code(url, timeout=90):
    """Status code without following redirects (multi-DB stacks redirect /web/login to the
    selector with a Location that does not carry the published port)."""
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        return opener.open(url, timeout=timeout).status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def do_project(name, dry=False):
    db, app, cdir, svc, conf_rel, port = PROJECTS[name]
    compose = f'{BASE}/{cdir}/docker-compose.yml'
    conf = f'{BASE}/{conf_rel}'
    secret = f'{BASE}/secrets/{name}.pgpass'
    print(f'\n=== {name}  ({app}, {cdir}/{svc})')
    text = open(compose).read()
    if re.search(r'\.pgpass:/var/lib/odoo/\.pgpass', text) and name in text and f'secrets/{name}.pgpass' in text:
        print('   already migrated, skipping'); return True
    new_compose = patch_compose(text, svc, app)
    new_compose = new_compose.replace('{name}', name)
    if dry:
        import difflib
        for l in difflib.unified_diff(text.splitlines(), new_compose.splitlines(), lineterm='', n=0):
            if not l.startswith(('---', '+++', '@@')):
                print('   ', re.sub(r'(PASSWORD\s*[=:]\s*).*', r'\1<redacted>', l))
        return True
    uid = sh('docker', 'exec', app, 'id', '-u').strip(); gid = sh('docker', 'exec', app, 'id', '-g').strip()
    old_pw = sh('docker', 'exec', BACKEND, 'printenv', 'DB_PASSWORD').strip()
    os.makedirs(f'{BK}/{name}', exist_ok=True)
    shutil.copy2(compose, f'{BK}/{name}/docker-compose.yml')
    shutil.copy2(conf, f'{BK}/{name}/odoo.conf')
    os.chmod(f'{BK}/{name}', 0o700)
    new_pw = secrets.token_urlsafe(24)
    esc = lambda v: v.replace('\\', '\\\\').replace(':', '\\:')
    pgpass_line = f'*:5432:*:odoo_app:{esc(new_pw)}\n'

    def restore():
        print('   !! rolling back')
        try:
            set_role_password(db, old_pw)
        except Exception as e:
            print('      role password restore failed:', e)
        shutil.copy2(f'{BK}/{name}/docker-compose.yml', compose)
        data = open(f'{BK}/{name}/odoo.conf').read()
        backend_py(f"import os\nopen(os.environ['P'],'w').write(os.environ['D'])\n", P=conf, D=data)
        backend_py("import os\ntry: os.remove(os.environ['P'])\nexcept FileNotFoundError: pass\n", P=secret)
        sh('docker', 'compose', 'up', '-d', '--no-deps', '--force-recreate', svc, cwd=f'{BASE}/{cdir}', check=False)

    try:
        # 1. secret file (root, owned by the container's odoo user)
        backend_py("import os\nd=os.path.dirname(os.environ['P']); os.makedirs(d, mode=0o700, exist_ok=True)\n"
                   "open(os.environ['P'],'w').write(os.environ['L']); os.chmod(os.environ['P'],0o600)\n"
                   "os.chown(os.environ['P'], int(os.environ['U']), int(os.environ['G']))\n",
                   P=secret, L=pgpass_line, U=uid, G=gid)
        # 2. role password + files
        set_role_password(db, new_pw)
        cdata = open(conf).read()
        cnew = re.sub(r'(?m)^db_password\s*=.*\n', '', cdata)
        backend_py("import os\nopen(os.environ['P'],'w').write(os.environ['D'])\n", P=conf, D=cnew)
        open(compose, 'w').write(new_compose)
        sh('docker', 'compose', 'config', '-q', cwd=f'{BASE}/{cdir}')
        # 3. recreate + verify
        sh('docker', 'compose', 'up', '-d', '--no-deps', '--force-recreate', svc, cwd=f'{BASE}/{cdir}')
        ok = False
        for _ in range(40):
            if http_code(f'http://127.0.0.1:{port}/web/health') == 200:
                ok = True; break
            time.sleep(3)
        if not ok:
            raise RuntimeError('application did not become healthy')
        listing = backend_py(
            "import os, json, django\nos.environ.setdefault('DJANGO_SETTINGS_MODULE','core.settings')\n"
            "import sys; sys.path.insert(0,'/app'); django.setup()\n"
            "from services.registry import get_project\nfrom services import db_service\n"
            "p = get_project(os.environ['N'])\nr = db_service.list_databases(p['db_port'])\n"
            "print(json.dumps(r if isinstance(r, dict) else [d['name'] for d in r]))\n", N=name).strip().splitlines()[-1]
        names = json.loads(listing)
        if isinstance(names, dict):
            raise RuntimeError(f'dashboard cannot list databases: {names}')
        print(f'   dashboard lists: {names}')
        # DB-touching request through Odoo itself
        for dbn in names[:1]:
            code = http_code(f'http://127.0.0.1:{port}/web/login?db={dbn}')
            print(f'   login page for {dbn}: {code}')
            if not (200 <= code < 400):
                raise RuntimeError('login page failed')
        top = sh('docker', 'exec', app, 'sh', '-c', "tr '\\0' ' ' < /proc/1/cmdline")
        if 'db_password' in top:
            raise RuntimeError('db_password still visible in process arguments')
        logs = sh('docker', 'logs', '--since', '2m', app, check=False)
        if 'password authentication failed' in logs:
            raise RuntimeError('authentication failures in the application log')
        print('   OK: healthy, DB reachable via ~/.pgpass, no password in argv/conf/compose')
        return True
    except Exception as e:
        print('   FAILED:', e)
        restore()
        return False


def main():
    args = sys.argv[1:]
    dry = '--dry-run' in args
    names = [a for a in args if not a.startswith('--')]
    if '--all' in args:
        names = list(PROJECTS)
    if not names:
        print(__doc__); sys.exit(2)
    for n in names:
        if n not in PROJECTS:
            print('unknown project', n); sys.exit(2)
    os.makedirs(BK, mode=0o700, exist_ok=True)
    print('backups:', BK)
    for n in names:
        if not do_project(n, dry):
            print(f'\nStopped at {n}; earlier projects stay migrated.'); sys.exit(1)
    print('\nDone.')


if __name__ == '__main__':
    main()
