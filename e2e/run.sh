#!/usr/bin/env bash
# Convenience runner for the end-to-end suite.
#
#   ./e2e/run.sh          # bring up stack, seed, run all e2e tests, tear down
#   E2E_KEEP_STACK=1 ./e2e/run.sh   # leave containers up afterwards
#
# Requires: docker + docker compose v2, and the migrator installed:
#   pip install -e . && pip install -r e2e/requirements-e2e.txt
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE/.."

command -v migrate-rg >/dev/null 2>&1 || {
  echo "migrate-rg not found on PATH — run: pip install -e ." >&2
  exit 1
}

exec pytest e2e -m e2e -v "$@"
