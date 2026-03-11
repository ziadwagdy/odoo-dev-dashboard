import os
import subprocess
import shutil
from pathlib import Path

from services.registry import read_registry


ODOO_DEV_BASE = os.environ.get('ODOO_DEV_BASE', '/srv/odoo-dev')
PROJECTS_DIR = f'{ODOO_DEV_BASE}/projects'
WORKTREES_DIR = f'{ODOO_DEV_BASE}/worktrees'


def get_next_ports():
    """Determine next available Odoo and DB ports from registry."""
    projects = read_registry()
    
    used_odoo_ports = {int(p['odoo_port']) for p in projects if p.get('odoo_port')}
    used_db_ports = {int(p['db_port']) for p in projects if p.get('db_port')}
    
    # Start from 8072 for Odoo, 15433 for DB
    odoo_port = 8072
    while odoo_port in used_odoo_ports:
        odoo_port += 1
    
    db_port = 15433
    while db_port in used_db_ports:
        db_port += 1
    
    return odoo_port, db_port


def check_project_exists(project_name):
    """Check if project directory already exists."""
    project_dir = Path(PROJECTS_DIR) / project_name
    return project_dir.exists()


def check_worktrees_exist(version):
    """Verify worktrees exist for given Odoo version."""
    hr_base = Path(WORKTREES_DIR) / f'hr-base-{version}'
    enterprise = Path(WORKTREES_DIR) / f'enterprise-{version}'
    
    return hr_base.exists() and enterprise.exists()


def validate_project_name(name):
    """Validate project name (slug format)."""
    if not name:
        return False, "Project name is required"
    if not name.replace('-', '').replace('_', '').isalnum():
        return False, "Project name must be alphanumeric with hyphens/underscores"
    if ' ' in name:
        return False, "Project name cannot contain spaces"
    return True, None


def validate_subdomain(subdomain):
    """Validate subdomain format."""
    if not subdomain:
        return False, "Subdomain is required"
    if not subdomain.replace('-', '').isalnum():
        return False, "Subdomain must be alphanumeric with hyphens"
    return True, None


def clone_repository(repo_url, project_name, progress_callback):
    """Clone git repository with submodules."""
    project_dir = Path(PROJECTS_DIR) / project_name
    repo_dir = project_dir / 'repo'
    
    try:
        project_dir.mkdir(parents=True, exist_ok=True)
        
        progress_callback(f"Cloning {repo_url}...")
        result = subprocess.run(
            ['git', 'clone', '--recurse-submodules', repo_url, str(repo_dir)],
            capture_output=True, text=True, timeout=300
        )
        
        if result.returncode != 0:
            raise Exception(f"Git clone failed: {result.stderr}")
        
        progress_callback("Repository cloned successfully")
        
        # Initialize submodules if any
        if (repo_dir / '.gitmodules').exists():
            progress_callback("Initializing submodules...")
            subprocess.run(
                ['git', 'submodule', 'update', '--init', '--recursive'],
                cwd=repo_dir, check=True, capture_output=True
            )
            progress_callback("Submodules initialized")
        
        return True, str(repo_dir)
    except Exception as e:
        return False, str(e)


def detect_addons(repo_dir):
    """Find all addon directories containing __manifest__.py."""
    addons = []
    repo_path = Path(repo_dir)
    
    for manifest in repo_path.rglob('__manifest__.py'):
        addon_dir = manifest.parent
        addons.append(str(addon_dir.relative_to(repo_path)))
    
    return sorted(addons)


def build_addons_path(version, hr_base_mode):
    """Build the addons_path string for odoo.conf."""
    parts = [
        '/usr/lib/python3/dist-packages/odoo/addons',
        '/mnt/enterprise-addons',
    ]
    
    if hr_base_mode == 'yes-mount':
        parts.append('/mnt/hr-base-addons')
    
    parts.append('/mnt/project-addons')
    
    return ','.join(parts)


def create_docker_stack(project_name, version, odoo_port, db_port, 
                        addons_path, hr_base_mode, repo_dir, progress_callback):
    """Create Docker Compose stack files."""
    project_dir = Path(PROJECTS_DIR) / project_name
    config_dir = project_dir / 'config'
    config_dir.mkdir(exist_ok=True)
    
    # Copy requirements.txt if exists
    requirements_src = Path(repo_dir) / 'requirements.txt'
    requirements_dst = project_dir / 'requirements.txt'
    
    if requirements_src.exists():
        shutil.copy(requirements_src, requirements_dst)
        progress_callback(f"Copied requirements.txt")
    else:
        requirements_dst.touch()
        progress_callback("No requirements.txt found, created empty file")
    
    # Create Dockerfile
    dockerfile_content = f"""FROM odoo:{version}.0

USER root

COPY requirements.txt /tmp/requirements.txt
RUN if [ -f /tmp/requirements.txt ] && [ -s /tmp/requirements.txt ]; then \\
      pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements.txt 2>/dev/null || \\
      pip3 install --no-cache-dir -r /tmp/requirements.txt; \\
    fi

USER odoo
"""
    (project_dir / 'Dockerfile').write_text(dockerfile_content)
    progress_callback("Created Dockerfile")
    
    # Create odoo.conf
    odoo_conf_content = f"""[options]
addons_path = {addons_path}
data_dir = /var/lib/odoo

db_host = db-{project_name}
db_port = 5432
db_user = odoo
db_password = odoo

list_db = True
max_cron_threads = 1
log_level = info
workers = 0
"""
    (config_dir / 'odoo.conf').write_text(odoo_conf_content)
    progress_callback("Created odoo.conf")
    
    # Create docker-compose.yml
    volumes_section = f"""    volumes:
      - ./config:/etc/odoo:ro
      - ./repo:/mnt/project-addons:ro
      - ~/odoo-dev/worktrees/enterprise-{version}:/mnt/enterprise-addons:ro"""
    
    if hr_base_mode == 'yes-mount':
        volumes_section += f"""
      - ~/odoo-dev/worktrees/hr-base-{version}:/mnt/hr-base-addons:ro"""
    
    docker_compose_content = f"""services:
  db-{project_name}:
    image: postgres:15-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: postgres
      POSTGRES_USER: odoo
      POSTGRES_PASSWORD: odoo
    volumes:
      - db-data:/var/lib/postgresql/data
    ports:
      - "{db_port}:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U odoo"]
      interval: 10s
      timeout: 5s
      retries: 5

  {project_name}-app:
    build: .
    restart: unless-stopped
    depends_on:
      db-{project_name}:
        condition: service_healthy
    ports:
      - "{odoo_port}:8069"
{volumes_section}
    environment:
      - HOST=db-{project_name}
      - USER=odoo
      - PASSWORD=odoo

volumes:
  db-data:
"""
    (project_dir / 'docker-compose.yml').write_text(docker_compose_content)
    progress_callback("Created docker-compose.yml")
    
    return True


def build_docker_image(project_name, progress_callback):
    """Build Docker image."""
    project_dir = Path(PROJECTS_DIR) / project_name
    
    progress_callback("Building Docker image...")
    
    process = subprocess.Popen(
        ['docker', 'compose', 'build'],
        cwd=project_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    for line in process.stdout:
        line = line.strip()
        if line:
            progress_callback(f"  {line}")
    
    process.wait()
    
    if process.returncode != 0:
        raise Exception(f"Docker build failed with code {process.returncode}")
    
    progress_callback("Docker image built successfully")
    return True


def start_containers(project_name, progress_callback):
    """Start Docker containers."""
    project_dir = Path(PROJECTS_DIR) / project_name
    
    progress_callback("Starting containers...")
    
    result = subprocess.run(
        ['docker', 'compose', 'up', '-d'],
        cwd=project_dir,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise Exception(f"Failed to start containers: {result.stderr}")
    
    progress_callback("Containers started successfully")
    return True


def configure_cloudflare(subdomain, odoo_port, progress_callback):
    """Add Cloudflare tunnel configuration."""
    try:
        # Add DNS route
        progress_callback(f"Configuring DNS for {subdomain}.zedev.org...")
        subprocess.run(
            ['cloudflared', 'tunnel', 'route', 'dns', 'odoo-dev', f'{subdomain}.zedev.org'],
            check=True, capture_output=True
        )
        progress_callback("DNS record created")
        
        # Update config file
        progress_callback("Updating tunnel configuration...")
        config_file = '/etc/cloudflared/config.yml'
        
        # Read current config
        with open(config_file, 'r') as f:
            lines = f.readlines()
        
        # Find the catch-all 404 service line
        insert_index = None
        for i, line in enumerate(lines):
            if 'http_status:404' in line:
                insert_index = i
                break
        
        if insert_index is None:
            raise Exception("Could not find catch-all service in tunnel config")
        
        # Insert new ingress rule before the catch-all
        new_rule = f"""  - hostname: {subdomain}.zedev.org
    service: http://localhost:{odoo_port}
"""
        lines.insert(insert_index, new_rule)
        
        # Write back
        with open(config_file, 'w') as f:
            f.writelines(lines)
        
        progress_callback("Tunnel configuration updated")
        
        # Restart cloudflared
        progress_callback("Restarting tunnel service...")
        subprocess.run(['systemctl', 'restart', 'cloudflared'], check=True)
        progress_callback("Tunnel service restarted")
        
        return True
    except Exception as e:
        progress_callback(f"Warning: Cloudflare configuration failed: {e}")
        return False


def update_registry(project_name, version, odoo_port, db_port, subdomain):
    """Add project to port registry."""
    registry_file = Path(PROJECTS_DIR) / '.port-registry'
    
    # folder is the actual directory name (same as project_name in most cases)
    folder = project_name
    
    entry = f"{project_name}|{version}|{odoo_port}|{db_port}|{subdomain}.zedev.org|projects/{folder}\n"
    
    with open(registry_file, 'a') as f:
        f.write(entry)
    
    return True
