import os, sys, json, urllib.request, urllib.error
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings"); sys.path.insert(0, "/app"); django.setup()
from django.contrib.auth.models import User, Group
from rest_framework.authtoken.models import Token
from apps.projects.models import UserProjectAssignment, AuditLog
from core.authentication import mark_active

BASE = "http://nginx:80"   # the dashboard's own nginx container (same path real browsers use)
PROJECT, DB = "omc-holding", "omc-test"
names = {"admin": "zz-test-admin", "manager": "zz-test-manager", "developer": "zz-test-developer"}
tokens = {}
try:
    for role, uname in names.items():
        u, _ = User.objects.get_or_create(username=uname)
        u.set_unusable_password(); u.save()
        u.groups.set([Group.objects.get(name=role)])
        UserProjectAssignment.objects.get_or_create(user=u, project_name=PROJECT)
        t = Token.objects.create(user=u); mark_active(t.key); tokens[role] = t.key

    def call(role, method, path, body=None):
        req = urllib.request.Request(BASE + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Authorization": f"Token {tokens[role]}", "Content-Type": "application/json", "Host": "localhost"})
        try:
            r = urllib.request.urlopen(req, timeout=60); return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            raw = e.read() or b"{}"
            try: return e.code, json.loads(raw)
            except Exception: return e.code, {"raw": raw[:120].decode("utf-8", "replace")}

    print(f"database {DB} neutralized:", call("admin", "GET", f"/api/db/{PROJECT}/login-users/{DB}")[1].get("neutralized"))
    for role in ("developer", "manager", "admin"):
        s, d = call(role, "GET", f"/api/db/{PROJECT}/login-users/{DB}")
        adm = [u for u in d["users"] if u["admin"]][0]; ordi = [u for u in d["users"] if not u["admin"]][0]
        print(f"{role:9} list: admin-target allowed={adm['allowed']} reason_required={adm['reason_required']} | ordinary allowed={ordi['allowed']} reason_required={ordi['reason_required']}")
    adm_login = [u for u in call("admin", "GET", f"/api/db/{PROJECT}/login-users/{DB}")[1]["users"] if u["admin"]][0]["login"]
    ord_login = [u for u in call("admin", "GET", f"/api/db/{PROJECT}/login-users/{DB}")[1]["users"] if not u["admin"]][0]["login"]
    print("developer -> admin target          :", call("developer", "POST", f"/api/db/{PROJECT}/login-link/{DB}", {"login": adm_login, "reason": "please let me in now"})[0], "(expect 403)")
    print("manager   -> admin, no reason      :", call("manager", "POST", f"/api/db/{PROJECT}/login-link/{DB}", {"login": adm_login})[0], "(expect 400)")
    s, d = call("manager", "POST", f"/api/db/{PROJECT}/login-link/{DB}", {"login": adm_login, "reason": "live walkthrough of phase 1 policy"})
    print("manager   -> admin, with reason    :", s, "(expect 200) link host ok:", d.get("url", "").startswith("https://"))
    s, d = call("developer", "POST", f"/api/db/{PROJECT}/login-link/{DB}", {"login": ord_login})
    print("developer -> ordinary user         :", s, "(expect 200)")
    print("developer deploy                   :", call("developer", "POST", f"/api/project/{PROJECT}/deploy")[0], "(expect 403)")
    print("manager   deploy                   :", call("manager", "POST", f"/api/project/{PROJECT}/deploy")[0], "(expect 403)")
    print("developer approve a request        :", call("developer", "POST", f"/api/settings/{PROJECT}/changes/1/approve", {"confirm": True})[0], "(expect 403)")
    print("--- audit rows written by this walkthrough:")
    for a in AuditLog.objects.filter(user__startswith="zz-test-").order_by("id"):
        print(f"   {a.user:18} {a.action:15} {a.outcome:8} ip={a.ip or '-':8} target={a.meta.get('target')} reason={a.meta.get('reason')!r}")
finally:
    Token.objects.filter(user__username__in=names.values()).delete()
    UserProjectAssignment.objects.filter(user__username__in=names.values()).delete()
    User.objects.filter(username__in=names.values()).delete()
    print("temporary users removed:", not User.objects.filter(username__in=names.values()).exists())
