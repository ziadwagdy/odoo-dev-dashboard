import psutil
from concurrent.futures import ThreadPoolExecutor, as_completed

from services.docker_service import get_container_stats, get_container_status


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
