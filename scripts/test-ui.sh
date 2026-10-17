#!/usr/bin/env bash
# Headless-Chrome UI tests (Playwright) against the running dashboard, in BOTH themes.
# Creates throwaway dashboard users (an admin and a developer), runs the suite in a Playwright
# container, ALWAYS deletes the users again. Screenshots land in ~/ui-test-artifacts/<timestamp>/.
#   scripts/test-ui.sh                  # whole suite
#   scripts/test-ui.sh -g "Settings"    # any playwright arguments
set -euo pipefail
cd "$(dirname "$0")/.."
PW_VERSION=${PW_VERSION:-1.49.0}
OUT=${UI_ARTIFACTS:-$HOME/ui-test-artifacts}/$(date +%Y%m%d-%H%M%S)
mkdir -p "$OUT"; chmod 777 "$OUT"
BACKEND=odoo-dev-dashboard-backend-1
PROJECT=${UI_PROJECT:-omc-holding}

cleanup() {
  docker exec -i "$BACKEND" sh -c 'cd /app && python -' >/dev/null 2>&1 <<'PY' || true
import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings"); django.setup()
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from apps.projects.models import UserProjectAssignment
names = ["zz-ui-admin", "zz-ui-developer"]
Token.objects.filter(user__username__in=names).delete()
UserProjectAssignment.objects.filter(user__username__in=names).delete()
User.objects.filter(username__in=names).delete()
PY
}
trap cleanup EXIT

TOKENS=$(docker exec -i -e PROJECT="$PROJECT" "$BACKEND" sh -c 'cd /app && python -' <<'PY'
import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings"); django.setup()
from django.contrib.auth.models import User, Group
from rest_framework.authtoken.models import Token
from apps.projects.models import UserProjectAssignment
from core.authentication import mark_active
out = {}
for role, uname in (("admin", "zz-ui-admin"), ("developer", "zz-ui-developer")):
    u, _ = User.objects.get_or_create(username=uname); u.set_unusable_password(); u.save()
    u.groups.set([Group.objects.get(name=role)])
    UserProjectAssignment.objects.get_or_create(user=u, project_name=os.environ["PROJECT"])
    Token.objects.filter(user=u).delete(); t = Token.objects.create(user=u); mark_active(t.key); out[role] = t.key
print(out["admin"], out["developer"])
PY
)
read -r TOKEN_ADMIN TOKEN_DEV <<<"$TOKENS"

set +e
docker run --rm --network host --ipc=host \
  -e UI_TOKEN_ADMIN="$TOKEN_ADMIN" -e UI_TOKEN_DEV="$TOKEN_DEV" -e UI_PROJECT="$PROJECT" \
  -e UI_BASE_URL="${UI_BASE_URL:-http://127.0.0.1:8892}" -e PW_VERSION="$PW_VERSION" \
  -v "$PWD/frontend/e2e":/src/e2e:ro -v "$OUT":/artifacts \
  "mcr.microsoft.com/playwright:v${PW_VERSION}-jammy" \
  bash -c 'mkdir -p /work && cp -r /src/e2e/. /work/ && cd /work && npm init -y >/dev/null 2>&1 \
           && npm i -D --no-audit --no-fund --loglevel=error @playwright/test@"$PW_VERSION" >/dev/null \
           && npx playwright test --config=playwright.config.ts "$@"' playwright-runner "$@"
rc=$?
echo "screenshots: $OUT"
exit $rc
