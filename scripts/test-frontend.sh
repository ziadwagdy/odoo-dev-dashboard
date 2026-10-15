#!/usr/bin/env bash
# Frontend unit tests in a throwaway node container (nothing is written into the repo).
set -euo pipefail
cd "$(dirname "$0")/../frontend"
exec docker run --rm -v "$PWD":/src:ro node:20-alpine sh -c \
  'cp -r /src /app && cd /app && npm install --no-audit --no-fund --loglevel=error >/dev/null && npx vitest run "$@"' sh "$@"
