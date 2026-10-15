#!/usr/bin/env bash
# Run the backend test suite in a throwaway container built from the same code and
# dependencies as production (Docker build target `test`). No Docker socket, no network,
# no access to real projects: Docker/Postgres/filesystem are faked at the boundary.
#
#   scripts/test-backend.sh                 # everything
#   scripts/test-backend.sh -k settings     # any pytest arguments
#   scripts/test-backend.sh --cov-report ...
set -euo pipefail
cd "$(dirname "$0")/.."
docker build -q --target test -t odoo-dev-dashboard-backend-test backend >/dev/null
exec docker run --rm --network none odoo-dev-dashboard-backend-test pytest "$@"
