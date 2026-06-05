"""Self-bootstrapping start script: runs migrations then execs gunicorn.

Works regardless of CWD (Render runs from the repo root by default).
- Adds `backend/` to sys.path so `spotter_backend.settings` resolves.
- Runs `manage.py migrate` once before serving.
- Re-execs into gunicorn so the PID is correct for Render's health check.

`migrate` is fast and idempotent — no harm running it on every cold start.
"""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND_DIR = HERE / "backend"
sys.path.insert(0, str(BACKEND_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "spotter_backend.settings")

import django  # noqa: E402

django.setup()
from django.core.management import call_command  # noqa: E402

try:
    call_command("migrate", interactive=False, verbosity=1)
except Exception as e:
    print(f"migrate failed (continuing): {e}", file=sys.stderr)

try:
    call_command("seed_demo", verbosity=0)
except Exception:
    pass

cmd = [
    "gunicorn",
    "spotter_backend.wsgi:application",
    "--bind", f"0.0.0.0:{os.environ.get('PORT', '10000')}",
    "--workers", "2",
    "--timeout", "60",
]
os.chdir(BACKEND_DIR)
os.execvp(cmd[0], cmd)
