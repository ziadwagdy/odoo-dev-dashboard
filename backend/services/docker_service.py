import docker

_client = None


def get_docker_client():
    global _client
    if _client is None:
        _client = docker.from_env()
    return _client


def get_container_status(name):
    try:
        client = get_docker_client()
        container = client.containers.get(name)
        return container.status
    except docker.errors.NotFound:
        return 'not_found'
    except Exception:
        return 'error'


def restart_container(name):
    client = get_docker_client()
    container = client.containers.get(name)
    container.restart()


def stop_container(name):
    client = get_docker_client()
    container = client.containers.get(name)
    container.stop()


def get_container_stats(name):
    try:
        client = get_docker_client()
        container = client.containers.get(name)
        stats = container.stats(stream=False)
        cpu_delta = (
            stats['cpu_stats']['cpu_usage']['total_usage']
            - stats['precpu_stats']['cpu_usage']['total_usage']
        )
        sys_delta = (
            stats['cpu_stats'].get('system_cpu_usage', 0)
            - stats['precpu_stats'].get('system_cpu_usage', 0)
        )
        num_cpus = stats['cpu_stats'].get('online_cpus') or len(
            stats['cpu_stats']['cpu_usage'].get('percpu_usage', [1])
        )
        cpu_pct = (cpu_delta / sys_delta) * num_cpus * 100.0 if sys_delta > 0 else 0.0
        
        # Debug logging
        print(f"[{name}] cpu_delta={cpu_delta}, sys_delta={sys_delta}, cpu%={cpu_pct:.1f}")
        
        mem = stats['memory_stats']
        mem_used = mem.get('usage', 0) - mem.get('stats', {}).get('cache', 0)
        mem_limit = mem.get('limit', 1)
        return {
            'cpu_pct':      round(cpu_pct, 1),
            'mem_used_mb':  round(mem_used / 1024 / 1024, 1),
            'mem_limit_mb': round(mem_limit / 1024 / 1024, 1),
        }
    except Exception:
        return None


def get_container_logs(name, tail=500, follow=False):
    try:
        client = get_docker_client()
        container = client.containers.get(name)
        for chunk in container.logs(stream=True, follow=follow, tail=tail, timestamps=True):
            yield chunk
    except Exception:
        return


def exec_in_container(name, cmd):
    try:
        client = get_docker_client()
        container = client.containers.get(name)
        result = container.exec_run(cmd, stream=True, demux=False)
        return result.exit_code, result.output
    except Exception as e:
        return 1, iter([str(e).encode()])
