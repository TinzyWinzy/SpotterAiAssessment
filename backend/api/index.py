"""
Vercel serverless entry point for Django.

Wraps the WSGI app so Vercel can route all requests to Django.
Set DJANGO_SETTINGS_MODULE=spotter_backend.settings in the Vercel project env.
"""

import os
import sys
from pathlib import Path

# Allow the project root to be importable.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "spotter_backend.settings")

from spotter_backend.wsgi import application  # noqa: E402

# Vercel's Python runtime looks for a top-level `app` callable.
app = application
