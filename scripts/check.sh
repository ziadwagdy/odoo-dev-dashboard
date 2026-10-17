#!/usr/bin/env bash
# One command before and after every change:  scripts/check.sh [--live] [--ui]
#   default : backend + frontend unit tests (no Docker socket, no real projects)
#   --live  : additionally the read-only smoke test against the running platform
#   --ui    : additionally the headless-Chrome UI tests (both themes) against the running dashboard
set -euo pipefail
cd "$(dirname "$0")/.."
echo "### backend tests";  scripts/test-backend.sh
echo "### frontend tests"; scripts/test-frontend.sh
for arg in "$@"; do
  case "$arg" in
    --live) echo "### live smoke"; scripts/smoke.sh ;;
    --ui)   echo "### headless Chrome UI (dark + light)"; scripts/test-ui.sh ;;
  esac
done
echo "ALL CHECKS PASSED"
