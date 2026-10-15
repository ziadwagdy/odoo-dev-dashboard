import os
import secrets
import subprocess
import shutil
from pathlib import Path

from django.conf import settings

from services.registry import read_registry


ODOO_DEV_BASE = os.environ.get('ODOO_DEV_BASE', '/home/zeyad/odoo-dev')
WORKTREES_DIR = f'{ODOO_DEV_BASE}/worktrees'


# ── helpers ──────────────────────────────────────────────────────────

def _log(emit, text, error=False):
    emit({'type': 'log', 'text': text, 'error': error})


def _get_docker_used_ports() -> set:
    """Return all host ports reserved by Docker — running containers AND compose files.

    Scanning only running containers misses ports claimed by stopped containers,
    which causes collisions when a container is temporarily down during onboarding.
    """
    import re
    used = set()

    # Source 1: running containers via Docker socket
    try:
        import docker
        client = docker.from_env()
        for container in client.containers.list():
            for bindings in (container.ports or {}).values():
                if bindings:
                    for b in bindings:
                        try:
                            used.add(int(b['HostPort']))
                        except (KeyError, ValueError, TypeError):
                            pass
    except Exception:
        pass

    # Source 2: all docker-compose.yml files (catches stopped/removed containers)
    compose_port_re = re.compile(r'[\'"]\d+\.\d+\.\d+\.\d+:(\d+):\d+[\'"]|[\'"](\d+):\d+[\'"]')
    try:
        for compose_file in Path(ODOO_DEV_BASE).glob('*/docker-compose.yml'):
            text = compose_file.read_text()
            for m in compose_port_re.finditer(text):
                host_port = m.group(1) or m.group(2)
                if host_port:
                    try:
                        used.add(int(host_port))
                    except ValueError:
                        pass
    except Exception:
        pass

    return used


# ── validation ───────────────────────────────────────────────────────

def get_next_ports():
    projects = read_registry()
    used_odoo = {int(p['odoo_port']) for p in projects if p.get('odoo_port')}
    used_db   = {int(p['db_port'])   for p in projects if p.get('db_port')}

    # Also account for ports already bound on the host by running containers
    # (the registry may not yet list a container that's already up)
    docker_ports = _get_docker_used_ports()
    used_odoo |= docker_ports
    used_db   |= docker_ports

    odoo_port = 8072
    while odoo_port in used_odoo:
        odoo_port += 1

    db_port = 15433
    while db_port in used_db:
        db_port += 1

    return odoo_port, db_port


def check_project_exists(project_name):
    return (Path(ODOO_DEV_BASE) / project_name).exists()


def check_worktrees_exist(version):
    enterprise = Path(WORKTREES_DIR) / f'enterprise-{version}'
    if not enterprise.exists():
        return False
    hr_base = Path(WORKTREES_DIR) / f'hr-base-{version}'
    # hr-base is optional — not every Odoo version has a matching branch
    # v15 only has enterprise; yes-mount will be blocked in the UI for those versions
    return True


def hr_base_worktree_exists(version):
    return (Path(WORKTREES_DIR) / f'hr-base-{version}').exists()


def validate_project_name(name):
    if not name:
        return False, 'Project name is required'
    if not name.replace('-', '').replace('_', '').isalnum():
        return False, 'Project name must be alphanumeric with hyphens/underscores'
    if ' ' in name:
        return False, 'Project name cannot contain spaces'
    return True, None


def validate_subdomain(subdomain):
    if not subdomain:
        return False, 'Subdomain is required'
    if not subdomain.replace('-', '').isalnum():
        return False, 'Subdomain must be alphanumeric with hyphens'
    return True, None


# ── onboarding steps ─────────────────────────────────────────────────

def cleanup_project(project_name, emit):
    """Remove a partial project directory after a failed onboard."""
    project_dir = Path(ODOO_DEV_BASE) / project_name
    if not project_dir.exists():
        return
    try:
        # Repo files may be owned by the odoo Docker user — use chmod first
        subprocess.run(['chmod', '-R', '777', str(project_dir)], capture_output=True)
        shutil.rmtree(str(project_dir))
        _log(emit, f'Cleaned up partial project directory')
    except Exception as e:
        _log(emit, f'Could not auto-clean {project_dir}: {e} — remove it manually with: sudo rm -rf {project_dir}', error=True)


def clone_repository(repo_url, project_name, emit):
    project_dir = Path(ODOO_DEV_BASE) / project_name
    repo_dir    = project_dir / 'repo'
    try:
        project_dir.mkdir(parents=True, exist_ok=True)

        if not repo_url:
            repo_dir.mkdir(exist_ok=True)
            _log(emit, 'No repository URL provided — created empty addons directory')
            return True, str(repo_dir)

        _log(emit, f'Cloning {repo_url}…')
        result = subprocess.run(
            ['git', 'clone', '--recurse-submodules', repo_url, str(repo_dir)],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode != 0:
            raise Exception(f'Git clone failed: {result.stderr.strip()}')
        _log(emit, 'Repository cloned successfully')

        if (repo_dir / '.gitmodules').exists():
            _log(emit, 'Initialising submodules…')
            subprocess.run(
                ['git', 'submodule', 'update', '--init', '--recursive'],
                cwd=repo_dir, check=True, capture_output=True,
            )
            _log(emit, 'Submodules initialised')

        return True, str(repo_dir)
    except Exception as e:
        return False, str(e)


def detect_addons(repo_dir):
    addons = []
    for manifest in Path(repo_dir).rglob('__manifest__.py'):
        addons.append(str(manifest.parent.relative_to(repo_dir)))
    return sorted(addons)


def build_addons_path(version, hr_base_mode, addons=()):
    """addons: module paths relative to the repo root (from detect_addons).
    Every directory that directly holds a module becomes an entry, so nested
    layouts — e.g. a cnc-hr-base submodule ('yes-included') — are covered."""
    parts = [
        '/usr/lib/python3/dist-packages/odoo/addons',
        '/mnt/enterprise-addons',
    ]
    if hr_base_mode == 'yes-mount':
        parts.append('/mnt/hr-base-addons')
    parts.append('/mnt/project-addons')

    module_dirs = set(addons)
    container_dirs = set()
    for addon in addons:
        parent = Path(addon).parent
        # Skip modules nested inside another module (e.g. test fixtures)
        if any(str(p) in module_dirs for p in parent.parents if str(p) != '.') or str(parent) in module_dirs:
            continue
        if str(parent) != '.':
            container_dirs.add(parent.as_posix())
    parts.extend(f'/mnt/project-addons/{d}' for d in sorted(container_dirs))
    return ','.join(parts)


def create_docker_stack(project_name, version, odoo_port, db_port,
                        addons_path, hr_base_mode, repo_dir, emit):
    project_dir = Path(ODOO_DEV_BASE) / project_name
    config_dir  = project_dir / 'config'
    config_dir.mkdir(exist_ok=True)

    # requirements.txt — merge from project repo AND mounted worktrees
    req_dst = project_dir / 'requirements.txt'
    scan_roots = [Path(repo_dir)]
    if hr_base_mode in ('yes-mount', 'yes-included'):
        hr_base_dir = Path(WORKTREES_DIR) / f'hr-base-{version}'
        if hr_base_dir.exists():
            scan_roots.append(hr_base_dir)

    all_req_files = []
    for root in scan_roots:
        all_req_files.extend(sorted(root.rglob('requirements*.txt')))

    if all_req_files:
        seen, lines = set(), []
        for req_file in all_req_files:
            try:
                for line in req_file.read_text(errors='replace').splitlines():
                    stripped = line.strip()
                    if stripped and not stripped.startswith('#') and stripped not in seen:
                        seen.add(stripped)
                        lines.append(stripped)
            except Exception:
                pass
        req_dst.write_text('\n'.join(lines) + '\n' if lines else '')
        _log(emit, f'Merged {len(all_req_files)} requirements file(s) from repo + worktrees → {len(lines)} package(s)')
    else:
        req_dst.touch()
        _log(emit, 'No requirements.txt found — created empty file')

    # Dockerfile
    (project_dir / 'Dockerfile').write_text(f"""FROM odoo:{version}.0

USER root
COPY requirements.txt /tmp/requirements.txt
RUN if [ -f /tmp/requirements.txt ] && [ -s /tmp/requirements.txt ]; then \\
      pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements.txt 2>/dev/null || \\
      pip3 install --no-cache-dir -r /tmp/requirements.txt; \\
    fi
USER odoo
""")
    _log(emit, 'Created Dockerfile')

    # admin_passwd
    admin_passwd = secrets.token_urlsafe(12)

    # The dashboard connects to every project DB as settings.DB_USER (see
    # db_service._connect), so the project's Postgres + Odoo must use that same
    # role — otherwise the Database/Notebook tabs cannot see or restore DBs.
    #
    # SECURITY: that role must NOT be a superuser. A superuser reachable over
    # the shared odoo-dbnet with a guessable password allows
    # COPY ... FROM PROGRAM (the 2026-09-02 cryptominer incident). So the
    # Postgres bootstrap superuser gets a random per-project password that the
    # app/dashboard never use, and db_user is created as a plain LOGIN+CREATEDB
    # role by an initdb script.
    db_user = settings.DB_USER
    db_password = settings.DB_PASSWORD
    pg_admin_user = 'odoo'
    pg_admin_password = secrets.token_urlsafe(24)

    initdb_dir = project_dir / 'initdb'
    initdb_dir.mkdir(exist_ok=True)
    (initdb_dir / '01-app-role.sql').write_text(
        f"CREATE ROLE \"{db_user}\" LOGIN CREATEDB NOSUPERUSER NOCREATEROLE "
        f"PASSWORD '{db_password.replace(chr(39), chr(39) * 2)}';\n"
    )
    # Must stay world-readable: the postgres user inside the container reads it
    (initdb_dir / '01-app-role.sql').chmod(0o644)

    # odoo.conf
    (config_dir / 'odoo.conf').write_text(f"""[options]
admin_passwd = {admin_passwd}
addons_path = {addons_path}
data_dir = /var/lib/odoo

db_host = db-{project_name}
db_port = 5432
db_user = {db_user}
db_password = {db_password}

list_db = True
proxy_mode = True
max_cron_threads = 1
log_level = info
workers = 2
limit_time_cpu = 600
limit_time_real = 1200
""")
    _log(emit, 'Created odoo.conf')

    # Emit the password as a structured credential event — UI will show it prominently
    emit({'type': 'credential', 'label': 'DB Manager master password', 'value': admin_passwd})

    # PostgreSQL version
    pg_version = {'15': '14', '17': '15'}.get(str(version), '16')

    # Volume mounts (absolute paths — Docker doesn't expand ~)
    volume_lines = [
        f'      - ./config/odoo.conf:/etc/odoo/odoo.conf:ro',
        f'      - app-data:/var/lib/odoo',
        f'      - ./repo:/mnt/project-addons:ro',
        f'      - {ODOO_DEV_BASE}/worktrees/enterprise-{version}:/mnt/enterprise-addons:ro',
    ]
    if hr_base_mode == 'yes-mount':
        volume_lines.append(
            f'      - {ODOO_DEV_BASE}/worktrees/hr-base-{version}:/mnt/hr-base-addons:ro'
        )

    # docker-compose.yml
    (project_dir / 'docker-compose.yml').write_text(f"""services:
  db-{project_name}:
    image: postgres:{pg_version}-alpine
    container_name: {project_name}-db
    restart: unless-stopped
    environment:
      POSTGRES_DB: postgres
      POSTGRES_USER: {pg_admin_user}
      POSTGRES_PASSWORD: {pg_admin_password}
    volumes:
      - db-data:/var/lib/postgresql/data
      - ./initdb:/docker-entrypoint-initdb.d:ro
    ports:
      # Loopback only (host `psql` convenience). The dashboard reaches this DB
      # by container name on the shared `odoo-dbnet` network, not via this port.
      - "127.0.0.1:{db_port}:5432"
    networks:
      - default
      - odoo-dbnet
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U {pg_admin_user}"]
      interval: 10s
      timeout: 5s
      retries: 5

  {project_name}-app:
    build: .
    container_name: {project_name}-app
    restart: unless-stopped
    depends_on:
      db-{project_name}:
        condition: service_healthy
    ports:
      - "127.0.0.1:{odoo_port}:8069"
    volumes:
{chr(10).join(volume_lines)}
    environment:
      - HOST=db-{project_name}
      - USER={db_user}
      - PASSWORD={db_password}

networks:
  default:
  odoo-dbnet:
    external: true

volumes:
  db-data:
  app-data:
""")
    _log(emit, 'Created docker-compose.yml')


def build_docker_image(project_name, emit):
    project_dir = Path(ODOO_DEV_BASE) / project_name
    _log(emit, 'Starting build…')
    process = subprocess.Popen(
        ['docker', 'compose', 'build'],
        cwd=project_dir,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True,
    )
    for line in process.stdout:
        line = line.strip()
        if line:
            emit({'type': 'log', 'text': line, 'phase': 'build'})
    process.wait()
    if process.returncode != 0:
        raise Exception(f'Docker build failed with exit code {process.returncode}')
    _log(emit, 'Docker image built successfully')


def start_containers(project_name, emit):
    project_dir = Path(ODOO_DEV_BASE) / project_name
    _log(emit, 'Bringing containers up…')
    result = subprocess.run(
        ['docker', 'compose', 'up', '-d'],
        cwd=project_dir, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise Exception(f'docker compose up failed: {result.stderr.strip()}')
    _log(emit, 'Containers started')


def verify_db_access(project_name, emit, timeout=90):
    """Connect to the new project's Postgres exactly as the dashboard does.

    Fails the onboarding loudly if the dashboard role/password can't log in,
    instead of leaving a project whose DB list is silently empty.
    """
    import time
    import psycopg2
    host = f'{project_name}-db'
    deadline = time.time() + timeout
    last_err = None
    while time.time() < deadline:
        try:
            conn = psycopg2.connect(
                host=host, port=5432, user=settings.DB_USER,
                password=settings.DB_PASSWORD, dbname='postgres', connect_timeout=5,
            )
            conn.close()
            _log(emit, f'Dashboard DB access verified ({settings.DB_USER}@{host})')
            return
        except Exception as e:
            last_err = e
            time.sleep(3)
    raise Exception(
        f'Dashboard cannot connect to {host} as {settings.DB_USER}: {last_err}'
    )


def update_dozzle(project_name, emit):
    """Add the new project's app container to Dozzle's filter and restart it."""
    dozzle_compose = Path(ODOO_DEV_BASE) / 'dozzle' / 'docker-compose.yml'
    if not dozzle_compose.exists():
        _log(emit, 'Dozzle compose not found — skipping', error=False)
        return
    try:
        content = dozzle_compose.read_text()
        container_name = f'{project_name}-app'
        if container_name in content:
            _log(emit, f'Dozzle already includes {container_name}')
            return
        # Append to the filter value: name=a|b|c → name=a|b|c|new-app
        import re
        content = re.sub(
            r'(DOZZLE_FILTER:\s*"[^"]+)',
            lambda m: m.group(0) + f'|{container_name}',
            content,
        )
        dozzle_compose.write_text(content)
        result = subprocess.run(
            ['docker', 'compose', 'up', '-d'],
            cwd=str(dozzle_compose.parent),
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            _log(emit, f'Dozzle updated — {container_name} is now visible in logs')
        else:
            _log(emit, f'Dozzle restart failed: {result.stderr.strip()}', error=True)
    except Exception as e:
        _log(emit, f'Could not update Dozzle: {e}', error=True)


def update_registry(project_name, version, odoo_port, db_port, subdomain):
    registry_file = Path(settings.REGISTRY_FILE)
    folder    = f'{project_name}/repo'
    conf_file = f'{project_name}/config/odoo.conf'
    entry = f'{project_name}|{version}|{odoo_port}|{db_port}|{subdomain}.zedev.org|{folder}|{conf_file}\n'
    with open(registry_file, 'a') as f:
        f.write(entry)


def configure_nginx(project_name, subdomain, odoo_port, emit):
    """Write nginx.conf to the project dir and emit a manual_step event."""
    nginx_conf = f"""upstream {project_name} {{ server 127.0.0.1:{odoo_port}; keepalive 2; }}

server {{
    listen 80;
    server_name {subdomain}.zedev.org;
    proxy_read_timeout 720s;
    proxy_connect_timeout 720s;
    proxy_send_timeout 720s;
    proxy_buffering off;
    proxy_http_version 1.1;
    proxy_redirect off;
    client_max_body_size 512m;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Real-IP $remote_addr;
    add_header X-Frame-Options SAMEORIGIN;
    add_header X-Content-Type-Options nosniff;
    access_log /var/log/nginx/{project_name}.access.log;
    error_log /var/log/nginx/{project_name}.error.log;
    location / {{ proxy_pass http://{project_name}; }}
    gzip_types text/css text/less text/plain application/json application/javascript;
    gzip on;
}}"""

    try:
        nginx_path = Path(ODOO_DEV_BASE) / project_name / 'nginx.conf'
        nginx_path.write_text(nginx_conf)
    except Exception:
        pass

    emit({
        'type': 'manual_step',
        'id': 'nginx',
        'label': 'Activate Nginx',
        'items': [
            {'kind': 'note',    'text': 'Config file written to ~/odoo-dev/{}/nginx.conf'.format(project_name)},
            {'kind': 'command', 'text': 'sudo cp ~/odoo-dev/{name}/nginx.conf /etc/nginx/conf.d/{name}.conf'.format(name=project_name)},
            {'kind': 'command', 'text': 'sudo nginx -t && sudo systemctl reload nginx'},
        ],
    })


def configure_cloudflare(subdomain, emit):
    """Emit a manual_step event with Cloudflare tunnel instructions."""
    cf_yaml = f'  - hostname: {subdomain}.zedev.org\n    service: http://localhost:80'
    emit({
        'type': 'manual_step',
        'id': 'cloudflare',
        'label': 'Cloudflare Tunnel',
        'items': [
            {'kind': 'note',    'text': 'Register the DNS record:'},
            {'kind': 'command', 'text': f'cloudflared tunnel route dns hrdev {subdomain}.zedev.org'},
            {'kind': 'note',    'text': 'Add to /etc/cloudflared/config.yml — before the catch-all line:'},
            {'kind': 'code',    'text': cf_yaml},
            {'kind': 'command', 'text': 'sudo systemctl restart cloudflared'},
        ],
    })


# ── port allocation (bulk) ────────────────────────────────────────────

def get_next_n_port_pairs(n):
    projects = read_registry()
    used_odoo = {int(p['odoo_port']) for p in projects if p.get('odoo_port')}
    used_db   = {int(p['db_port'])   for p in projects if p.get('db_port')}
    docker_ports = _get_docker_used_ports()
    used_odoo |= docker_ports
    used_db   |= docker_ports
    pairs = []
    odoo, db = 8072, 15433
    while len(pairs) < n:
        while odoo in used_odoo:
            odoo += 1
        while db in used_db:
            db += 1
        pairs.append((odoo, db))
        used_odoo.add(odoo); used_db.add(db)
        odoo += 1; db += 1
    return pairs
