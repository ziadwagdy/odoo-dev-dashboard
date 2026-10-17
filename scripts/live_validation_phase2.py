import os, sys, time, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings"); sys.path.insert(0, "/app"); django.setup()
from django.conf import settings
from services.registry import read_registry, get_project
from services import db_service, lifecycle

def listing(p): return [d["name"] for d in db_service.list_databases(p["db_port"])]

print("== 1. neutralization state of every database (the new badge)")
for p in read_registry():
    states = []
    for d in listing(p):
        try: states.append(f"{d}={'yes' if db_service.database_state(p['db_port'], d)['neutralized'] else 'NO'}")
        except Exception as e: states.append(f"{d}=?({str(e)[:30]})")
    print(f"  {p['name']:12} " + ", ".join(states))

print("== 2. live restore test on vodafone (backup -> scratch DB -> checks -> drop)")
p = get_project("vodafone"); bdir = os.path.join(settings.DATA_DIR, "backups", "vodafone")
path, name = db_service.backup_database(p["db_port"], "vodafone", bdir)
r = lifecycle.restore_check("vodafone", p["db_port"], path, bdir)
print("  result:", {k: r[k] for k in ("ok", "checks", "seconds", "error")})
left = [d for d in listing(p) if d.startswith("zz-restore-test-")]
print("  scratch databases left behind:", left or "none")

print("== 3. live module update with snapshot (dashboard_login on omc-test)")
p = get_project("omc-holding"); out = []
code = lifecycle.run_module_update("omc-holding", p["db_port"], "omc-test", "dashboard_login",
                                   lambda l: out.append(l), os.path.join(settings.DATA_DIR, "backups", "omc-holding"))
print("  exit code:", code); [print("  |", l[:150]) for l in out[:6]]; print("  ... lines:", len(out))
snaps = [f for f in os.listdir(os.path.join(settings.DATA_DIR, "backups", "omc-holding")) if f.startswith("pre-update-")]
print("  snapshots on disk:", snaps)
