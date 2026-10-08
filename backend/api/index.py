"""Vercel entry point if project root is configured as backend/."""

import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
ROOT_DIR = os.path.dirname(BACKEND_DIR)

for path in [BACKEND_DIR, ROOT_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)

try:
    from backend.app.main import app
except ImportError:
    from app.main import app
