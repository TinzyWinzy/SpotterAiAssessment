#!/usr/bin/env bash
# Idempotent DB bootstrap. Safe to run on every start.
# Renders DB is ephemeral on the free tier, so we re-migrate + re-seed
# on every boot. seed_demo is a no-op if the demo data already exists.
set -o errexit
cd "$(dirname "$0")"
python manage.py migrate --no-input
python manage.py seed_demo >/dev/null 2>&1 || true
