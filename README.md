# Odoo Dev Dashboard

A lightweight Flask dashboard for managing multi-version Odoo development environments running in Docker.

![Dashboard Preview](https://img.shields.io/badge/Flask-3.0-blue) ![Docker](https://img.shields.io/badge/Docker-required-2496ED) ![License](https://img.shields.io/badge/license-MIT-green)

## Overview

When running multiple Odoo projects (different versions, different clients) on a single server, keeping track of what's running, where it lives, and how to access it becomes tedious. This dashboard solves that by reading a simple registry file and showing the live status of every project in one place.

**Features:**
- Live running/stopped status per container
- Projects grouped by Odoo version
- One-click open, logs, and restart per project
- Infrastructure shortcuts (Logs, File Browser, Terminal)
- Auto-refreshes every 30 seconds
- Fully configurable via environment variables — no hardcoded values

## How It Works

The dashboard reads a plain-text **port registry** file where each line describes one Odoo project:

```
name|odoo_version|odoo_port|db_port|url
```

Example:
```
odoo17|17|8069|15432|v17.example.com
odoo18|18|8070|5433|v18.example.com
medtech|19|8072|15433|medtech.example.com
lexus|17|8073|15434|lexus.example.com
```

For each entry it:
1. Derives the container name as `{name}-app`
2. Calls `docker inspect` to check if it's running
3. Renders a card with Open / Logs / Restart actions

The **Logs** button resolves the container's Docker ID and redirects directly to that container's log stream in [Dozzle](https://dozzle.dev).

The **Restart** button sends a `POST /restart/<container>` request and reloads the page once done.

## Project Structure

```
dashboard/
├── app.py              # Flask routes
├── config.py           # Configuration from environment variables
├── requirements.txt
├── docker-compose.yml
├── .env                # Your actual config (gitignored)
├── .env.example        # Safe template to copy from
├── .gitignore
├── templates/
│   └── index.html      # Jinja2 template
└── static/
    ├── style.css
    └── app.js
```

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/odoo-dev-dashboard.git
cd odoo-dev-dashboard
```

### 2. Create your `.env`

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
REGISTRY_FILE=/path/to/your/.port-registry
BASE_DOMAIN=example.com
LOGS_URL=https://logs.example.com
FILES_URL=https://files.example.com
TERMINAL_URL=https://terminal.example.com
DASHBOARD_TITLE=Odoo Dev Dashboard
PORT=8891
```

### 3. Create your port registry file

The path must match `REGISTRY_FILE` in your `.env`. Format:

```
name|odoo_version|odoo_port|db_port|public_url
```

### 4. Run with Docker Compose

```bash
docker compose up -d
```

The dashboard will be available at `http://localhost:8891`.

### Running locally (without Docker)

```bash
pip install -r requirements.txt
export $(cat .env | xargs)
python app.py
```

> **Note:** The Logs and Restart features require the Docker socket (`/var/run/docker.sock`) to be accessible. When running locally, this works automatically. In Docker, the socket is mounted in `docker-compose.yml`.

## Configuration Reference

| Variable | Description | Default |
|---|---|---|
| `REGISTRY_FILE` | Path to the port registry file | `/data/projects/.port-registry` |
| `BASE_DOMAIN` | Your root domain | `example.com` |
| `LOGS_URL` | URL of your Dozzle instance | `https://logs.{BASE_DOMAIN}` |
| `FILES_URL` | URL of your File Browser instance | `https://files.{BASE_DOMAIN}` |
| `TERMINAL_URL` | URL of your web terminal (e.g. Wetty) | `https://terminal.{BASE_DOMAIN}` |
| `DASHBOARD_TITLE` | Browser tab title | `Odoo Dev Dashboard` |
| `PORT` | Port the Flask app listens on | `8891` |

## Infrastructure Assumptions

This dashboard is designed to work alongside:

| Tool | Purpose |
|---|---|
| [Dozzle](https://dozzle.dev) | Container log viewer |
| [FileBrowser](https://filebrowser.xyz) | Web-based file manager |
| [Wetty](https://github.com/butlerx/wetty) | Web-based terminal |
| [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) | Public HTTPS URLs without open ports |

None of these are required — the dashboard works without them, but the infrastructure shortcut cards and Logs redirect won't have valid targets.

## API

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Dashboard UI |
| `/api/status` | GET | JSON list of all projects with running status |
| `/logs/<container>` | GET | Redirects to Dozzle container log stream |
| `/restart/<container>` | POST | Restarts the Docker container |

## License

MIT
# odoo-dev-dashboard
