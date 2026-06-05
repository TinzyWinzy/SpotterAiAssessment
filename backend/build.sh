#!/usr/bin/env bash
# Render runs this at deploy time. Must end in a running web process.
# `release` would be cleaner, but on Render free tier it can race the
# web boot; the safe path is to migrate right before gunicorn starts.
set -o errexit
pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate --no-input
python manage.py seed_demo || true
exec gunicorn spotter_backend.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 60
