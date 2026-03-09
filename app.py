#!/usr/bin/env python3
import os
import subprocess

from flask import Flask, jsonify, redirect, render_template

import config

app = Flask(__name__)


# ── helpers ──────────────────────────────────────────────────────────────────

def is_container_running(name):
    try:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Status}}", name],
            capture_output=True, text=True, timeout=3,
        )
        return result.stdout.strip() == "running"
    except Exception:
        return False


def read_registry():
    projects = []
    if not os.path.exists(config.REGISTRY_FILE):
        return projects
    with open(config.REGISTRY_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("|")
            if len(parts) >= 5:
                projects.append({
                    "name":       parts[0],
                    "version":    parts[1],
                    "odoo_port":  parts[2],
                    "db_port":    parts[3],
                    "url":        parts[4],
                    "container":  f"{parts[0]}-app",
                })
    return projects


def get_projects_grouped():
    projects = read_registry()
    for p in projects:
        p["running"] = is_container_running(p["container"])
    grouped = {}
    for p in projects:
        grouped.setdefault(p["version"], []).append(p)
    return dict(sorted(grouped.items()))


# ── routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    return render_template(
        "index.html",
        grouped_projects=get_projects_grouped(),
        title=config.DASHBOARD_TITLE,
        base_domain=config.BASE_DOMAIN,
        logs_url=config.LOGS_URL,
        files_url=config.FILES_URL,
        terminal_url=config.TERMINAL_URL,
    )


@app.route("/restart/<container_name>", methods=["POST"])
def restart_container(container_name):
    try:
        subprocess.run(["docker", "restart", container_name], timeout=30)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/logs/<container_name>")
def container_logs(container_name):
    try:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.Id}}", container_name],
            capture_output=True, text=True, timeout=3,
        )
        container_id = result.stdout.strip()[:12]
        return redirect(f"{config.LOGS_URL}/container/{container_id}")
    except Exception:
        return redirect(config.LOGS_URL)


@app.route("/api/status")
def api_status():
    projects = read_registry()
    for p in projects:
        p["running"] = is_container_running(p["container"])
    return jsonify({"projects": projects})


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.PORT, debug=False)
