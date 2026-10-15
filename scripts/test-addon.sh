#!/usr/bin/env bash
# Contract test of the dashboard_login Odoo addon against REAL Odoo containers.
# Spins up a throwaway server on port 18999 inside each app container with a scratch
# database, exercises valid/replay/tamper/expired/over-long/unknown-user/wrong-db/open-redirect,
# then drops the scratch database. Use before changing the addon and before releases.
#   scripts/test-addon.sh                       # odoo17, odoo18, odoo19 stacks
#   scripts/test-addon.sh odoo19-app odoo19-db  # one stack (app container, db container)
set -uo pipefail
ADDONS="${ODOO_DEV_BASE:-$HOME/odoo-dev}/dashboard-addons"
HERE="$(cd "$(dirname "$0")" && pwd)"
stacks=("$@")
[ ${#stacks[@]} -eq 0 ] && stacks=(odoo17-app odoo17-db odoo18-app odoo18-db odoo19-app odoo19-db)
rc=0
for ((i=0; i<${#stacks[@]}; i+=2)); do
  app=${stacks[i]}; db=${stacks[i+1]}
  echo "=== $app"
  docker exec -u root "$app" sh -c 'rm -rf /tmp/dashboard-addons /tmp/addon_contract_test.py' 2>/dev/null
  docker cp "$ADDONS" "$app:/tmp/dashboard-addons" && docker cp "$HERE/addon_contract_test.py" "$app:/tmp/addon_contract_test.py"
  out=$(docker exec "$app" python3 /tmp/addon_contract_test.py 2>&1)
  echo "$out" | sed 's/^/   /'
  docker exec "$db" sh -c "psql -U \$(psql -U odoo -d postgres -tAc 'select 1' >/dev/null 2>&1 && echo odoo || echo pgroot) -d postgres -qc 'DROP DATABASE IF EXISTS \"zz-sso-test\"'" 2>/dev/null
  expected=$'valid link                 303'
  grep -q "valid link .* 303 .*web client loaded" <<<"$out" || { echo "   !! valid link did not log in"; rc=1; }
  for case in "replay of same link" "tampered signature" "expired link" "ttl too long" "unknown user"; do
    grep -q "^$case .* 403" <<<"$out" || { echo "   !! '$case' was not refused (403)"; rc=1; }
  done
  grep -q "^wrong db in token .* 400" <<<"$out" || { echo "   !! wrong db not refused (400)"; rc=1; }
  grep -q "open redirect blocked .* /web" <<<"$out" || { echo "   !! open redirect not neutralised"; rc=1; }
done
[ $rc -eq 0 ] && echo "addon contract: all passed" || echo "addon contract: FAILURES"
exit $rc
