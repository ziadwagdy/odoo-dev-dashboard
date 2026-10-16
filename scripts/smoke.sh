#!/usr/bin/env bash
# Read-only live checks. Run after every deploy:   scripts/smoke.sh
# Exit code 0 only if every check passes. Touches nothing; sends no credentials.
set -uo pipefail
BASE=${ODOO_DEV_BASE:-$HOME/odoo-dev}
DASH=${DASHBOARD_URL:-http://127.0.0.1:8892}
REG="$BASE/.port-registry"
pass=0; fail=0
ok()   { pass=$((pass+1)); printf '  \033[32mPASS\033[0m %s\n' "$1"; }
bad()  { fail=$((fail+1)); printf '  \033[31mFAIL\033[0m %s\n' "$1"; }
code() { curl -s -o /dev/null -m 15 -w '%{http_code}' "$@" 2>/dev/null || echo 000; }
expect() { # description, expected-regex, actual
  if [[ "$3" =~ ^($2)$ ]]; then ok "$1 ($3)"; else bad "$1: expected $2, got $3"; fi
}

echo "== dashboard"
expect "SPA served"                         "200"     "$(code $DASH/)"
expect "/api/auth/me needs a token"         "401"     "$(code $DASH/api/auth/me)"
expect "/stream/status needs a token"       "401"     "$(code $DASH/stream/status)"
expect "/stream/logs needs a token"         "401"     "$(code $DASH/stream/logs/odoo17-app)"
expect "settings need a token"              "401"     "$(code $DASH/api/settings/odoo17/runtime)"
expect "deploy needs a token"               "401"     "$(code -X POST $DASH/api/project/odoo17/deploy)"
expect "raw odoo.conf endpoint is gone"     "401|404" "$(code $DASH/api/settings/odoo17/odoo-conf)"
expect "webhook rejects unsigned requests"  "401|403" "$(code -X POST -H 'Content-Type: application/json' -d '{}' $DASH/api/git/webhook/github)"
ws=$(curl -s -i -N -m 4 -H "Connection: Upgrade" -H "Upgrade: websocket" -H "Sec-WebSocket-Version: 13" \
      -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" -H "Origin: https://evil.example" \
      $DASH/ws/notebook/odoo17 2>/dev/null | head -1)
[[ "$ws" == *101* ]] && bad "notebook websocket accepted an unauthenticated handshake" || ok "notebook websocket refuses unauthenticated handshakes"

echo "== projects (from $REG)"
if [ ! -r "$REG" ]; then bad "registry not readable"; else
  while IFS='|' read -r name version oport dbport url folder conf; do
    [[ -z "$name" || "$name" == \#* ]] && continue
    expect "$name: app healthy"                      "200"     "$(code http://127.0.0.1:$oport/web/health)"
    expect "$name: DB manager closed at the proxy"   "403"     "$(code -H "Host: $url" http://127.0.0.1/web/database/manager)"
    expect "$name: XML-RPC db service closed"        "403"     "$(code -X POST -H "Host: $url" http://127.0.0.1/xmlrpc/2/db)"
    args=$(docker exec "${name}-app" sh -c "tr '\\0' ' ' < /proc/1/cmdline" 2>/dev/null)
    if [[ "$args" == *db_password* || "$args" == *--db_password* ]]; then bad "$name: password visible in process arguments"; else ok "$name: no password in process arguments"; fi
    if grep -qE '^db_password' "$BASE/${conf}" 2>/dev/null; then bad "$name: db_password present in odoo.conf"; else ok "$name: no db_password in odoo.conf"; fi
  done < "$REG"
fi

echo "== database lifecycle safety"
admin_of() { for u in odoo pgroot; do
  [ "$(docker exec "$1" psql -U $u -d postgres -tAc "select rolsuper from pg_roles where rolname=current_user" 2>/dev/null)" = t ] && { echo $u; return; }; done; }
for c in $(docker ps --format '{{.Names}}' | grep -E -- '-db$'); do
  u=$(admin_of "$c"); [ -z "$u" ] && { bad "$c: no superuser reachable for the lifecycle check"; continue; }
  scratch=$(docker exec "$c" psql -U "$u" -d postgres -tAc "select count(*) from pg_database where datname like 'zz-restore-test-%'" 2>/dev/null)
  [ "$scratch" = "0" ] && ok "$c: no leftover restore-test databases" || bad "$c: $scratch leftover restore-test database(s)"
  open=$(docker exec "$c" psql -U "$u" -d postgres -tAc "select count(*) from pg_database where datname not in ('postgres','template0','template1') and (datacl is null or datacl::text ~ '(^\\{|,)=[A-Za-z]*c')" 2>/dev/null)
  [ "$open" = "0" ] && ok "$c: PUBLIC cannot connect to project databases" || bad "$c: $open database(s) connectable by PUBLIC"
done

echo "== detection"
backend_log=$(docker logs odoo-dev-dashboard-backend-1 2>&1)     # not "| grep -q": pipefail + SIGPIPE would misreport
if [[ "$backend_log" == *"security watcher started"* ]]; then ok "security watcher is running"; else bad "security watcher did not start"; fi
expect "security alerts need a token"       "401"     "$(code $DASH/api/security/alerts)"
expect "push subscription needs a token"    "401"     "$(code -X POST $DASH/api/push/subscribe)"
expect "service worker is served"           "200"     "$(code $DASH/sw.js)"

echo "== edge"
listen=$(ss -ltn 2>/dev/null | awk '$4 ~ /:80$/ {print $4}' | sort -u | tr '\n' ' ')
[[ "$listen" == "127.0.0.1:80 " ]] && ok "nginx listens on loopback only ($listen)" || bad "nginx listeners: ${listen:-none}"
pub=$(ss -ltn 2>/dev/null | awk '$4 ~ /^0\.0\.0\.0:|^\[::\]:/ {print $4}' | grep -vE ':22$' | tr '\n' ' ')
[[ -z "$pub" ]] && ok "no public listeners except SSH" || bad "unexpected public listeners: $pub"

echo
echo "passed: $pass  failed: $fail"
[ "$fail" -eq 0 ]
