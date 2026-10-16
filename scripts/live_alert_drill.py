import os, sys, time, django, psycopg2
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings"); sys.path.insert(0, "/app"); django.setup()
from services import db_service
from services.registry import get_project
from apps.security.models import SecurityAlert
p = get_project("cnc")
before = SecurityAlert.objects.count()
# 1. wrong password (auth failure)
try: psycopg2.connect(host="cnc-db", port=5432, user="odoo_app", password="drill-wrong-password", dbname="postgres", connect_timeout=4)
except Exception: pass
# 2. denied COPY ... FROM PROGRAM (non-superuser: permission denied, nothing executes)
conn = db_service._connect(p["db_port"]); conn.autocommit = True
try: conn.cursor().execute("CREATE TEMP TABLE _prog_out(x text); COPY _prog_out FROM PROGRAM 'echo alert-drill'")
except Exception as e: print("denied as expected:", str(e).splitlines()[0][:70])
conn.close()
time.sleep(6)
for a in SecurityAlert.objects.order_by("-id")[:5]:
    print(f"  alert #{a.id} {a.severity:8} {a.rule:16} {a.source:8} count={a.count} status={a.status} | {a.summary[:70]}")
print("new alerts:", SecurityAlert.objects.count() - before)
