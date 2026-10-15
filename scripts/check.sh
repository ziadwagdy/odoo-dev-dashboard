#!/usr/bin/env bash
# One command before and after every change:  scripts/check.sh [--live]
#   default : backend + frontend unit tests (no Docker socket, no real projects)
#   --live  : additionally the read-only smoke test against the running platform
set -euo pipefail
cd "$(dirname "$0")/.."
echo "### backend tests";  scripts/test-backend.sh
echo "### frontend tests"; scripts/test-frontend.sh
if [ "${1:-}" = "--live" ]; then echo "### live smoke"; scripts/smoke.sh; fi
echo "ALL CHECKS PASSED"
