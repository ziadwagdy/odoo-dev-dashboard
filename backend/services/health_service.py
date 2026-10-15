import os
import subprocess
import psutil
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.conf import settings
from services.docker_service import get_container_stats, get_container_status, get_docker_client


def get_host_stats() -> dict:
    cpu = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    return {
        'cpu_pct':       round(cpu, 1),
        'mem_used_mb':   round(mem.used / 1024 ** 2, 1),
        'mem_total_mb':  round(mem.total / 1024 ** 2, 1),
        'mem_pct':       round(mem.percent, 1),
        'disk_used_gb':  round(disk.used / 1024 ** 3, 1),
        'disk_total_gb': round(disk.total / 1024 ** 3, 1),
        'disk_pct':      round(disk.percent, 1),
    }


def _fetch_one(p: dict) -> dict:
    status = get_container_status(p['container'])
    stats = get_container_stats(p['container']) if status == 'running' else None
    mem_pct = None
    if stats and stats.get('mem_limit_mb'):
        mem_pct = round(stats['mem_used_mb'] / stats['mem_limit_mb'] * 100, 1)
    return {
        'name':         p['name'],
        'container':    p['container'],
        'status':       status,
        'cpu_pct':      stats['cpu_pct']      if stats else None,
        'mem_used_mb':  stats['mem_used_mb']  if stats else None,
        'mem_limit_mb': stats['mem_limit_mb'] if stats else None,
        'mem_pct':      mem_pct,
    }


def get_all_container_stats(projects: list) -> list:
    """Fetch stats for all containers in parallel."""
    if not projects:
        return []
    results = {}
    with ThreadPoolExecutor(max_workers=min(len(projects), 10)) as pool:
        futures = {pool.submit(_fetch_one, p): p['name'] for p in projects}
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception:
                results[name] = {
                    'name': name, 'container': f'{name}-app',
                    'status': 'error', 'cpu_pct': None,
                    'mem_used_mb': None, 'mem_limit_mb': None, 'mem_pct': None,
                }
    # Return in original registry order
    return [results[p['name']] for p in projects if p['name'] in results]


def _get_project_storage(project: dict) -> dict:
    name = project['name']
    container = project['container']
    folder = project.get('folder')
    db_port = project.get('db_port')

    filestore_bytes = 0
    code_bytes = 0
    db_bytes = 0

    # Filestore: exec du inside the app container
    try:
        client = get_docker_client()
        c = client.containers.get(container)
        result = c.exec_run('du -sb /var/lib/odoo', demux=False)
        if result.exit_code == 0:
            filestore_bytes = int(result.output.decode().split('\t')[0])
    except Exception:
        pass

    # Code repo: du on the folder path (ODOO_DEV_BASE is mounted in the backend)
    if folder:
        full_path = os.path.join(settings.ODOO_DEV_BASE, folder)
        try:
            r = subprocess.run(['du', '-sb', full_path], capture_output=True, text=True, timeout=15)
            if r.returncode == 0:
                code_bytes = int(r.stdout.split('\t')[0])
        except Exception:
            pass

    # Database: sum pg_database_size for all non-system DBs
    if db_port:
        try:
            from .db_service import _connect
            conn = _connect(db_port)
            cur = conn.cursor()
            cur.execute(
                "SELECT COALESCE(SUM(pg_database_size(datname)), 0) FROM pg_database "
                "WHERE datname NOT IN ('postgres','template0','template1')"
            )
            row = cur.fetchone()
            db_bytes = int(row[0]) if row else 0
            conn.close()
        except Exception:
            pass

    return {
        'name': name,
        'filestore_bytes': filestore_bytes,
        'code_bytes': code_bytes,
        'db_bytes': db_bytes,
        'total_bytes': filestore_bytes + code_bytes + db_bytes,
    }


def get_all_project_storage(projects: list) -> list:
    if not projects:
        return []
    results = {}
    with ThreadPoolExecutor(max_workers=min(len(projects), 6)) as pool:
        futures = {pool.submit(_get_project_storage, p): p['name'] for p in projects}
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception:
                results[name] = {
                    'name': name, 'filestore_bytes': 0, 'code_bytes': 0,
                    'db_bytes': 0, 'total_bytes': 0,
                }
    return sorted(
        [results[p['name']] for p in projects if p['name'] in results],
        key=lambda x: x['total_bytes'],
        reverse=True,
    )
