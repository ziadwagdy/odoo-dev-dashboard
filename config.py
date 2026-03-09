import os

REGISTRY_FILE = os.environ.get("REGISTRY_FILE", "/data/projects/.port-registry")
BASE_DOMAIN   = os.environ.get("BASE_DOMAIN", "example.com")
LOGS_URL      = os.environ.get("LOGS_URL",     f"https://logs.{BASE_DOMAIN}")
FILES_URL     = os.environ.get("FILES_URL",    f"https://files.{BASE_DOMAIN}")
TERMINAL_URL  = os.environ.get("TERMINAL_URL", f"https://terminal.{BASE_DOMAIN}")
DASHBOARD_TITLE = os.environ.get("DASHBOARD_TITLE", "Odoo Dev Dashboard")
PORT          = int(os.environ.get("PORT", 8891))
