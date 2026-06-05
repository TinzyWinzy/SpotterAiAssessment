#!/usr/bin/env bash
# Run the full test suite (backend pytest + frontend Playwright).
# Assumes Django on 8001 + Vite on 5173 are NOT already running —
# ensureServers() in _setup.ts will detect and reuse them if they are.

set -euo pipefail

cd "$(dirname "$0")/.."
ROOT=$(pwd)

echo "=== Backend tests ==="
cd "$ROOT/backend"
python -m pytest tests/ --tb=short

echo ""
echo "=== Frontend e2e tests ==="
cd "$ROOT/frontend"
npx playwright test --reporter=list

echo ""
echo "All tests passed."
