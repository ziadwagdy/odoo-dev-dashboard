# Plan: Rework Notebook to Real Jupyter Kernel (jupyter_client + ipykernel)

## Context

The current Notebook tab uses a custom homemade kernel: a bootstrap Python script injected into the Odoo container via Docker exec that communicates via JSON over stdin/stdout. It works for basic use but has critical limitations:

- **No kernel interruption** — a slow `env.search([])` hangs forever with no escape
- **No rich output** — cannot display pandas DataFrames as HTML tables, no matplotlib inline images
- **No proper tracebacks** — errors are plain text, no ANSI-formatted tracebacks
- **No tab completion**

The fix is to use the **real Jupyter kernel protocol**: `ipykernel` runs inside the Odoo container, `jupyter_client.BlockingKernelClient` connects from the backend over ZMQ. Both dependencies are already declared in `pyproject.toml`. The dashboard UI stays the same — no JupyterLab app, no separate tab. We gain rich output, interruption, and proper error formatting.

---

## Architecture

```
Browser (NotebookTab.vue)
    ↕  WebSocket  ws/notebook/{project}
Django Channels (consumers.py)
    ↕  thread + asyncio.Queue
kernel_manager.py  (BlockingKernelClient)
    ↕  ZMQ over TCP on Docker network
ipykernel process inside Odoo container
    ↕  internal
Odoo registry / env / self
```

**No port-forwarding or docker-compose changes needed.** The backend and Odoo containers are already on the same Docker network. The backend connects to the container's IP directly on fixed ZMQ ports.

---

## Files to Change

| File | Change |
|------|--------|
| `backend/apps/notebooks/kernel_manager.py` | **Full rewrite** — real jupyter_client protocol |
| `backend/apps/notebooks/consumers.py` | **Full rewrite** — status_callback, interrupt, rich output types |
| `frontend/src/components/NotebookTab.vue` | **Full rewrite** — HTML/image output, Interrupt button, status messages |
| `backend/pyproject.toml` | No change — `jupyter_client>=8.0` and `ipykernel>=6.0` already declared |
| `routing.py`, `urls.py`, `views.py` | No change — same WS route and REST endpoints |

---

## Key Design Decisions

### Fixed ZMQ ports inside every container

```
shell_port:   55001
iopub_port:   55002
stdin_port:   55003
control_port: 55004
hb_port:      55005
```

No conflicts — each container has its own network namespace.

### ipykernel auto-install

Odoo containers don't have ipykernel. `start_kernel()` checks then pip-installs on first use. Progress streamed to frontend via `status_callback`.

### Connection file written into container

`/tmp/_kernel_{project}.json` — standard Jupyter connection JSON with the fixed ports and a random HMAC key per session.

### Container IP lookup

```python
networks = container.attrs['NetworkSettings']['Networks']
ip = next(iter(networks.values()))['IPAddress']
```

### Odoo startup code (runs once after kernel ready)

```python
ODOO_STARTUP = """
import odoo, odoo.tools.config as cfg
from odoo.api import Environment
from odoo import SUPERUSER_ID
cfg.parse_config(['--no-http', '--stop-after-init'])
registry = odoo.registry('{db}')
_kernel_cursor = registry.cursor()
env = Environment(_kernel_cursor, SUPERUSER_ID, {{}})
self = env['res.users'].browse(SUPERUSER_ID)
import atexit
atexit.register(lambda: _kernel_cursor.close())
ip = get_ipython()
def _commit(result):
    try: _kernel_cursor.commit()
    except: pass
ip.events.register('post_execute', _commit)
print("✓ Odoo environment loaded. Database: {db}")
print("Available: env, self")
"""
```

One persistent cursor per session, auto-committed after each cell via IPython `post_execute` hook.

### Kernel interruption

```python
def interrupt_kernel(project_name):
    container.exec_run('pkill -INT -f ipykernel_launcher')
```

Sends SIGINT → Python raises `KeyboardInterrupt` → kernel stays alive, cell shows error, ready for next cell.

---

## WebSocket Protocol Changes

### Frontend → Backend (one addition)
```json
{"type": "interrupt"}   ← NEW
```

### Backend → Frontend (two additions)
```json
{"type": "status_message", "text": "Installing ipykernel..."}         ← NEW
{"type": "output", "cell_id": "x", "output_type": "html",  "data": "<table>..."}  ← NEW
{"type": "output", "cell_id": "x", "output_type": "image", "data": "base64png"}   ← NEW
```

All existing message types (`status`, `kernel_started`, `output/stdout`, `output/stderr`, `done`, `error`) remain identical.

---

## kernel_manager.py — Complete Rewrite

```python
"""
Manages real Jupyter kernels (ipykernel) running inside Odoo Docker containers.

Architecture:
  - ipykernel_launcher runs inside the container, listening on fixed ZMQ ports
  - jupyter_client.BlockingKernelClient connects from the backend to container IP
  - No port-forwarding needed: backend and Odoo containers share the Docker network
"""

import base64, json, threading, time, uuid
from jupyter_client import BlockingKernelClient
from services.docker_service import get_docker_client

KERNEL_PORTS = {
    "shell_port": 55001, "iopub_port": 55002, "stdin_port": 55003,
    "control_port": 55004, "hb_port": 55005,
}

ODOO_STARTUP = """\
import odoo, odoo.tools.config as cfg
from odoo.api import Environment
from odoo import SUPERUSER_ID
cfg.parse_config(['--no-http', '--stop-after-init'])
registry = odoo.registry('{db}')
_kernel_cursor = registry.cursor()
env = Environment(_kernel_cursor, SUPERUSER_ID, {{}})
self = env['res.users'].browse(SUPERUSER_ID)
import atexit; atexit.register(lambda: _kernel_cursor.close())
ip = get_ipython()
def _commit(result):
    try: _kernel_cursor.commit()
    except: pass
ip.events.register('post_execute', _commit)
print("\\u2713 Odoo environment loaded. Database: {db}")
print("Available: env, self")
"""

_kernels: dict[str, dict] = {}
_kernels_lock = threading.Lock()


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
    result = c.exec_run('pip install ipykernel --quiet', stream=False)
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
        container_ip = _get_container_ip(container_name)
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
    while time.time() < deadline:
        try:
            msg = kc.get_iopub_msg(timeout=5)
        except Exception:
            continue
        if (msg.get('parent_header', {}).get('msg_id') == msg_id
                and msg['msg_type'] == 'status'
                and msg['content'].get('execution_state') == 'idle'):
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
```

---

## consumers.py — Complete Rewrite

```python
import asyncio, json, threading
from channels.generic.websocket import AsyncWebsocketConsumer
from . import kernel_manager


class NotebookConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.project = self.scope['url_route']['kwargs']['project']
        await self.accept()
        await self.send(text_data=json.dumps({
            'type': 'status',
            'data': kernel_manager.get_kernel_status(self.project),
        }))

    async def receive(self, text_data):
        try:
            msg = json.loads(text_data)
            t = msg.get('type')
            if t == 'execute':
                await self.execute_cell(msg.get('code', ''), msg.get('cell_id', ''))
            elif t == 'start':
                await self.start_kernel(msg.get('db', ''))
            elif t == 'stop':
                kernel_manager.stop_kernel(self.project)
                await self.send(text_data=json.dumps({
                    'type': 'status',
                    'data': kernel_manager.get_kernel_status(self.project),
                }))
            elif t == 'interrupt':
                result = kernel_manager.interrupt_kernel(self.project)
                if not result.get('ok'):
                    await self.send(text_data=json.dumps({
                        'type': 'error', 'error': result.get('error', 'Interrupt failed'),
                    }))
        except Exception as exc:
            await self.send(text_data=json.dumps({'type': 'error', 'error': str(exc)}))

    async def start_kernel(self, db: str):
        if not db:
            await self.send(text_data=json.dumps({'type': 'error', 'error': 'db required'}))
            return
        container = f'{self.project}-app'
        loop = asyncio.get_running_loop()

        def status_callback(text: str):
            asyncio.run_coroutine_threadsafe(
                self.send(text_data=json.dumps({'type': 'status_message', 'text': text})),
                loop,
            )

        result = await loop.run_in_executor(
            None,
            lambda: kernel_manager.start_kernel(self.project, container, db, status_callback),
        )
        payload = {'type': 'kernel_started' if result.get('ok') else 'error', 'data': result}
        if not result.get('ok'):
            payload['error'] = result.get('error', 'Unknown error')
        await self.send(text_data=json.dumps(payload))
        await self.send(text_data=json.dumps({
            'type': 'status',
            'data': kernel_manager.get_kernel_status(self.project),
        }))

    async def execute_cell(self, code: str, cell_id: str):
        loop = asyncio.get_running_loop()
        out_queue: asyncio.Queue = asyncio.Queue()

        def _callback(output_type: str, data, oi_cell_id: str):
            if output_type == 'stream':
                ws_type = data['name']   # 'stdout' or 'stderr'
                ws_data = data['text']
            else:
                ws_type = output_type    # 'html', 'image', 'text', 'error'
                ws_data = data
            loop.call_soon_threadsafe(out_queue.put_nowait, (ws_type, ws_data))

        def _run():
            kernel_manager.execute_code(self.project, cell_id, code, _callback)
            loop.call_soon_threadsafe(out_queue.put_nowait, None)

        threading.Thread(target=_run, daemon=True).start()

        while True:
            item = await out_queue.get()
            if item is None:
                await self.send(text_data=json.dumps({'type': 'done', 'cell_id': cell_id}))
                break
            output_type, data = item
            await self.send(text_data=json.dumps({
                'type': 'output', 'cell_id': cell_id,
                'output_type': output_type, 'data': data,
            }))

    async def disconnect(self, close_code):
        pass
```

---

## NotebookTab.vue — Key Changes (diff summary)

The full component rewrite must:

1. **Handle `status_message` type** — show transient progress text (e.g. "Installing ipykernel…") with a pulsing dot indicator; auto-clear after `kernel_started`

2. **Handle `html` output type** — render with `v-html` in a styled div:
```html
<div v-if="out.type === 'html'"
     class="notebook-output-html px-3 py-2 overflow-x-auto"
     v-html="out.data" />
```

3. **Handle `image` output type** — render inline PNG:
```html
<img v-else-if="out.type === 'image'"
     :src="'data:image/png;base64,' + out.data"
     class="max-w-full h-auto rounded px-3 py-2" />
```

4. **Add Interrupt button** — enabled only when `anyRunning`:
```html
<button class="btn btn-warning btn-sm"
        :disabled="!anyRunning"
        @click="ws?.send(JSON.stringify({type:'interrupt'}))">
  ⏸ Interrupt
</button>
```

5. **Add `anyRunning` computed**:
```typescript
const anyRunning = computed(() => cells.value.some(c => c.status === 'running'))
```

6. **Scoped CSS for pandas DataFrames**:
```css
.notebook-output-html :deep(table) { border-collapse: collapse; font-size: 12px; color: #e2e8f0; }
.notebook-output-html :deep(th)    { background: #1e2130; padding: 4px 8px; border: 1px solid #2d3148; }
.notebook-output-html :deep(td)    { padding: 3px 8px; border: 1px solid #2d3148; }
.notebook-output-html :deep(tr:nth-child(even)) { background: #0f1117; }
```

7. **`btn-warning` class** — add to `style.css` if missing:
```css
.btn-warning { @apply bg-amber-600 hover:bg-amber-500 text-white rounded px-3 py-1.5 text-sm font-medium transition-colors; }
```

---

## Implementation Order

1. **`kernel_manager.py`** — write full file (copy from this plan verbatim)
2. **`consumers.py`** — write full file (copy from this plan verbatim)
3. **`NotebookTab.vue`** — update output rendering, add Interrupt button, status_message handler, scoped CSS
4. **`style.css`** — add `.btn-warning` if missing
5. `docker compose build backend && docker compose up -d backend` — only backend image changes
6. Rebuild frontend: `docker compose build frontend && docker compose up -d frontend`

---

## Verification

```bash
# 1. Confirm ZMQ connection works from backend to an Odoo container
docker exec dashboard-new-backend-1 python3 -c "
from apps.notebooks.kernel_manager import start_kernel, execute_code, stop_kernel
msgs = []
def cb(t, d, cid): msgs.append((t, repr(d)[:80]))
r = start_kernel('test', 'odoo17-app', 'mydb', lambda txt: print('STATUS:', txt))
print('start:', r)
execute_code('test', 'c1', 'print(1+1)', cb)
print('outputs:', msgs)
stop_kernel('test')
"

# 2. Pandas DataFrame → HTML table
# In browser Notebook tab: import pandas as pd; pd.DataFrame([{'a':1,'b':2},{'a':3,'b':4}])
# Expected: HTML table rendered with dark theme

# 3. Interrupt
# In browser Notebook tab: import time; time.sleep(999)
# Click Interrupt → KeyboardInterrupt shown, kernel stays alive

# 4. Matplotlib inline image
# import matplotlib; matplotlib.use('Agg')
# import matplotlib.pyplot as plt
# plt.plot([1,2,3,4]); plt.show()
# Expected: PNG image rendered inline
```
