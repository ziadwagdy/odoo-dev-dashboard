"""
Manages real Jupyter kernels (ipykernel) running inside Odoo Docker containers.

Architecture:
  - ipykernel_launcher runs inside the container, listening on fixed ZMQ ports
  - jupyter_client.BlockingKernelClient connects from the backend to container IP
  - No port-forwarding needed: backend and Odoo containers share the Docker network
"""

import base64, json, socket, threading, time, uuid
from jupyter_client import BlockingKernelClient
from services.docker_service import get_docker_client

KERNEL_PORTS = {
    'shell_port': 55001, 'iopub_port': 55002, 'stdin_port': 55003,
    'control_port': 55004, 'hb_port': 55005,
}

ODOO_STARTUP = """\
import odoo.tools.config as cfg
from odoo.modules.registry import Registry
from odoo.api import Environment, SUPERUSER_ID
cfg.parse_config(['--no-http', '--stop-after-init'])
registry = Registry.new('{db}')
_kernel_cursor = registry.cursor()
env = Environment(_kernel_cursor, SUPERUSER_ID, {{}})
self = env['res.users'].browse(SUPERUSER_ID)
import atexit; atexit.register(lambda: _kernel_cursor.close())
ip = get_ipython()
def _commit(*args):
    try: _kernel_cursor.commit()
    except: pass
ip.events.register('post_execute', _commit)
print("\u2713 Odoo environment loaded. Database: {db}")
print("Available: env, self")
"""

_kernels: dict[str, dict] = {}
_kernels_lock = threading.Lock()


def _ensure_backend_on_network(container_name: str, status_callback) -> str:
    """
    Ensure the backend container is on the same Docker network as the Odoo container.
    Returns the network name that should be used to reach the Odoo container.
    """
    client = get_docker_client()
    odoo_c = client.containers.get(container_name)
    odoo_networks = odoo_c.attrs['NetworkSettings']['Networks']
    if not odoo_networks:
        raise RuntimeError(f'Odoo container {container_name!r} has no networks')

    backend_hostname = socket.gethostname()
    try:
        backend_c = client.containers.get(backend_hostname)
        backend_networks = set(backend_c.attrs['NetworkSettings']['Networks'].keys())
        # If already sharing a network, use it
        for net_name in odoo_networks:
            if net_name in backend_networks:
                return net_name
        # Connect backend to the first Odoo network
        net_name = next(iter(odoo_networks))
        status_callback(f'Connecting to Docker network {net_name}…')
        client.networks.get(net_name).connect(backend_c.id)
        status_callback('Network connected')
        return net_name
    except Exception as exc:
        # Can't introspect ourselves (e.g. running outside Docker) — fall through
        # and use the first available network IP
        return next(iter(odoo_networks))


def _get_container_ip(container_name: str) -> str:
    c = get_docker_client().containers.get(container_name)
    networks = c.attrs['NetworkSettings']['Networks']
    if not networks:
        raise RuntimeError(f'Container {container_name!r} has no networks')
    ip = next(iter(networks.values()))['IPAddress']
    if not ip:
        raise RuntimeError(f'Container {container_name!r} has no IP')
    return ip


def _ensure_ipykernel(container_name: str, status_callback) -> None:
    c = get_docker_client().containers.get(container_name)
    check = c.exec_run("python3 -c \"import ipykernel; print('ok')\"")
    if check.exit_code == 0 and b'ok' in check.output:
        status_callback('ipykernel already installed')
        return
    status_callback('ipykernel not found — installing via pip (may take 30–60 s)…')
    result = c.exec_run('pip install ipykernel --quiet --break-system-packages', stream=False)
    if result.exit_code != 0:
        raise RuntimeError(f'pip install ipykernel failed:\n{result.output.decode(errors="replace")}')
    status_callback('ipykernel installed successfully')


def _write_connection_file(container_name: str, project_name: str, key: str) -> None:
    conn = {'ip': '0.0.0.0', 'transport': 'tcp',
            'signature_scheme': 'hmac-sha256', 'key': key, **KERNEL_PORTS}
    encoded = base64.b64encode(json.dumps(conn).encode()).decode()
    path = f'/tmp/_kernel_{project_name}.json'
    c = get_docker_client().containers.get(container_name)
    r = c.exec_run(f"sh -c 'echo {encoded} | base64 -d > {path}'", detach=False)
    if r.exit_code != 0:
        raise RuntimeError('Failed to write connection file into container')


def _launch_kernel_in_container(container_name: str, project_name: str) -> None:
    path = f'/tmp/_kernel_{project_name}.json'
    c = get_docker_client().containers.get(container_name)
    c.exec_run(f"sh -c 'pkill -f \"ipykernel_launcher.*{project_name}\" || true'", detach=False)
    time.sleep(0.5)
    c.exec_run(f'python3 -m ipykernel_launcher -f {path}', detach=True)


def start_kernel(project_name: str, container_name: str, db_name: str,
                 status_callback=None) -> dict:
    if status_callback is None:
        status_callback = lambda text: None
    with _kernels_lock:
        existing = _kernels.get(project_name)
        if existing and existing.get('db') == db_name and existing.get('status') == 'running':
            return {'ok': True, 'status': 'already_running', 'db': db_name}
        if existing:
            _stop_kernel_unlocked(project_name, existing)
            _kernels.pop(project_name, None)
    kc = None
    try:
        status_callback('Checking ipykernel installation…')
        _ensure_ipykernel(container_name, status_callback)
        key = str(uuid.uuid4())
        status_callback('Writing kernel connection file…')
        _write_connection_file(container_name, project_name, key)
        status_callback('Launching ipykernel inside container…')
        _launch_kernel_in_container(container_name, project_name)
        status_callback('Waiting for kernel heartbeat…')
        network_name = _ensure_backend_on_network(container_name, status_callback)
        # Reload container attrs after potential network join
        c = get_docker_client().containers.get(container_name)
        container_ip = c.attrs['NetworkSettings']['Networks'][network_name]['IPAddress']
        conn_info = {'ip': container_ip, 'transport': 'tcp',
                     'signature_scheme': 'hmac-sha256', 'key': key, **KERNEL_PORTS}
        kc = BlockingKernelClient()
        kc.load_connection_info(conn_info)
        kc.start_channels()
        kc.wait_for_ready(timeout=60)
        status_callback('Loading Odoo environment…')
        _run_startup_code(kc, db_name)
        with _kernels_lock:
            _kernels[project_name] = {
                'client': kc, 'container': container_name,
                'db': db_name, 'key': key, 'status': 'running',
            }
        status_callback('Kernel ready')
        return {'ok': True, 'status': 'running', 'db': db_name}
    except Exception as exc:
        try:
            kc.stop_channels()
        except Exception:
            pass
        return {'ok': False, 'error': str(exc)}


def _run_startup_code(kc: BlockingKernelClient, db_name: str) -> None:
    code = ODOO_STARTUP.format(db=db_name)
    msg_id = kc.execute(code)
    deadline = time.time() + 120
    error_text = None
    stdout_text = []
    while time.time() < deadline:
        try:
            msg = kc.get_iopub_msg(timeout=5)
        except Exception:
            continue
        if msg.get('parent_header', {}).get('msg_id') != msg_id:
            continue
        mt = msg['msg_type']
        content = msg['content']
        if mt == 'error':
            tb = '\n'.join(content.get('traceback', []))
            # Strip ANSI escape codes for a readable message
            import re
            clean = re.sub(r'\x1b\[[0-9;]*m', '', tb)
            error_text = f"{content.get('ename', 'Error')}: {content.get('evalue', '')}\n{clean}"
        elif mt == 'stream' and content.get('name') == 'stdout':
            stdout_text.append(content.get('text', ''))
        elif mt == 'status' and content.get('execution_state') == 'idle':
            if error_text:
                raise RuntimeError(f'Odoo startup failed:\n{error_text}')
            return
    raise RuntimeError('Odoo startup code did not complete within 120 s')


def execute_code(project_name: str, cell_id: str, code: str, output_callback) -> bool:
    kernel = _kernels.get(project_name)
    if not kernel or kernel['status'] != 'running':
        output_callback('error', 'No kernel running. Start a kernel first.', cell_id)
        return False
    kc: BlockingKernelClient = kernel['client']
    msg_id = kc.execute(code)
    while True:
        try:
            msg = kc.get_iopub_msg(timeout=120)
        except Exception:
            output_callback('error', 'Timeout or kernel became unresponsive', cell_id)
            return False
        msg_type = msg['msg_type']
        content = msg['content']
        parent_id = msg.get('parent_header', {}).get('msg_id', '')
        if parent_id != msg_id:
            continue
        if msg_type == 'stream':
            output_callback('stream', {'text': content['text'], 'name': content['name']}, cell_id)
        elif msg_type in ('display_data', 'execute_result'):
            data = content.get('data', {})
            if 'image/png' in data:
                output_callback('image', data['image/png'], cell_id)
            elif 'text/html' in data:
                output_callback('html', data['text/html'], cell_id)
            elif 'text/plain' in data:
                output_callback('text', data['text/plain'], cell_id)
        elif msg_type == 'error':
            output_callback('error', '\n'.join(content.get('traceback', [])), cell_id)
        elif msg_type == 'status' and content.get('execution_state') == 'idle':
            return True


def interrupt_kernel(project_name: str) -> dict:
    kernel = _kernels.get(project_name)
    if not kernel:
        return {'ok': False, 'error': 'no kernel running'}
    try:
        get_docker_client().containers.get(kernel['container']).exec_run(
            'pkill -INT -f ipykernel_launcher', detach=False)
        return {'ok': True}
    except Exception as exc:
        return {'ok': False, 'error': str(exc)}


def stop_kernel(project_name: str) -> dict:
    with _kernels_lock:
        kernel = _kernels.pop(project_name, None)
    if not kernel:
        return {'ok': False, 'error': 'no kernel running'}
    _stop_kernel_unlocked(project_name, kernel)
    return {'ok': True}


def _stop_kernel_unlocked(project_name: str, kernel: dict) -> None:
    try:
        kernel['client'].stop_channels()
    except Exception:
        pass
    try:
        get_docker_client().containers.get(kernel['container']).exec_run(
            f"pkill -f 'ipykernel_launcher.*{project_name}'", detach=False)
    except Exception:
        pass


def get_kernel_status(project_name: str) -> dict:
    kernel = _kernels.get(project_name)
    if kernel:
        return {'running': True, 'status': kernel.get('status'), 'db': kernel.get('db')}
    return {'running': False}
