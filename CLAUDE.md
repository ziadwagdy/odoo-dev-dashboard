# Odoo Dev Dashboard — CLAUDE.md

Modern Odoo development dashboard rewritten in Django + Vue 3. Replaces the old Flask dashboard at `../dashboard/`.

## Running the project

```bash
# From dashboard-new/
docker compose up -d          # start all services
docker compose logs -f        # tail logs
docker compose logs -f backend  # backend only

# Rebuild after code changes
docker compose build backend && docker compose up -d backend
docker compose build frontend && docker compose up -d frontend

# Full rebuild
docker compose build && docker compose up -d
```

**URL:** http://localhost:${PORT:-8892}

## Architecture

```
nginx (:${PORT:-8892})
  ├── /api/*    → backend (:8000, Django/Daphne ASGI)
  ├── /ws/*     → backend (Django Channels WebSocket)
  └── /*        → frontend (:80, Vite static build)
```

## Tech Stack

### Backend (`backend/`)
- **Django 5** + **Django REST Framework** — REST API
- **Django Channels** + **Daphne** — ASGI / WebSocket
- **SQLite** via Django ORM — deploy history, cron jobs
- **Redis** — Channels layer backend
- **APScheduler** — cron job scheduling
- **psutil** — host CPU/memory/disk stats
- **jupyter_client** + **ipykernel** — Notebook kernel protocol (ZMQ)

### Frontend (`frontend/src/`)
- **Vue 3** + **TypeScript** + **Vite**
- **Pinia** — state management
- **TailwindCSS** — styling

### Python Dependency Management
- Uses **`uv`** (NOT pip / requirements.txt)
- Config in `pyproject.toml`
- To add a package: edit `pyproject.toml` then rebuild backend image

## Project Structure

```
backend/
  apps/
    projects/        # start/stop/restart containers, backups, modules
    git_ops/         # branch management, pull, submodule sync
    notebooks/       # Jupyter kernel WebSocket (consumers.py + kernel_manager.py)
    settings_app/    # odoo.conf + .env editor, cron job CRUD
    streams/         # SSE streams: deploy logs, branch logs, health metrics
    database/        # DB create/drop/duplicate/restore
  services/
    registry.py      # read .port-registry; get_project(name) canonical lookup
    docker_service.py # get_docker_client() singleton
    git_service.py   # git operations via subprocess
    db_service.py    # psycopg2 DB ops, backup file listing
    health_service.py # get_host_stats(), get_all_container_stats() via psutil + Docker
    config_service.py # odoo.conf + .env read/write
    cron_scheduler.py # APScheduler job management
  core/
    settings.py
    asgi.py          # Channels routing entry point
    urls.py

frontend/src/
  views/
    DashboardView.vue    # main project list
    ProjectDetailView.vue # tabs: Deploy, Branch, Notebook, Settings, Database
    HealthView.vue       # system CPU/mem/disk + per-container stats
  components/
    ProjectCard.vue
    DeployPanel.vue
    BranchTab.vue
    NotebookTab.vue      # Jupyter notebook UI (WebSocket)
    SettingsTab.vue
    DatabaseTab.vue
    CpuGauge.vue         # reusable; accepts :value prop OR :container SSE mode
    MemoryBar.vue        # reusable; accepts direct props OR :container SSE mode
    StreamOutput.vue     # SSE log display
  stores/              # Pinia stores
  router/index.ts      # /  /project/:name  /health
```

## Key Conventions

### Registry
Port registry at `$ODOO_DEV_BASE/projects/.port-registry` (pipe-delimited):
```
name|version|odoo_port|db_port|url|folder
```
Always use `from services.registry import get_project` — do NOT duplicate `_get_project()` locally.

### Docker naming
Container name pattern: `{project_name}-app` (e.g. `odoo17-app`)

### SSE streams
- `GET /api/streams/deploy/{name}` — deploy log stream
- `GET /api/streams/branch/{name}` — branch-switch log stream
- `GET /api/streams/health/host` — host stats (every 2s)
- `GET /api/streams/health/containers` — all container stats (every 5s)

Always use `asyncio.get_running_loop()` (NOT deprecated `get_event_loop()`).
Always clean up queues in `finally` blocks of SSE generator functions.

### WebSocket — Notebook
`ws://.../ws/notebook/{project}`

**Frontend → Backend:**
```json
{"type": "start",     "db": "mydb"}
{"type": "execute",   "code": "...", "cell_id": "uuid"}
{"type": "interrupt"}
{"type": "stop"}
```

**Backend → Frontend:**
```json
{"type": "status",         "data": {"running": true, "db": "mydb"}}
{"type": "status_message", "text": "Installing ipykernel..."}
{"type": "kernel_started", "data": {...}}
{"type": "output",  "cell_id": "x", "output_type": "stdout",  "data": "..."}
{"type": "output",  "cell_id": "x", "output_type": "stderr",  "data": "..."}
{"type": "output",  "cell_id": "x", "output_type": "html",    "data": "<table>..."}
{"type": "output",  "cell_id": "x", "output_type": "image",   "data": "base64png"}
{"type": "output",  "cell_id": "x", "output_type": "text",    "data": "..."}
{"type": "output",  "cell_id": "x", "output_type": "error",   "data": "traceback"}
{"type": "done",    "cell_id": "x"}
{"type": "error",   "error": "..."}
```

### Database
- `DB_HOST=host.docker.internal`, `DB_USER=odoo`, `DB_PASSWORD=odoo`
- SQLite at `/app/data/db.sqlite3` — deploy history, cron jobs

## Environment Variables

See `.env.example`. Key vars:
```
REGISTRY_FILE=/srv/odoo-dev/projects/.port-registry
ODOO_DEV_BASE=/srv/odoo-dev
BASE_DOMAIN=your-domain.example.com
PORT=8892
SECRET_KEY=...
DB_USER=odoo
DB_PASSWORD=odoo
```


