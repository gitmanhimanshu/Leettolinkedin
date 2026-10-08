"""Vercel Serverless Function entry point for FastAPI backend."""

import os
import sys

# Ensure root directory and backend are on Python path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
for path in [ROOT_DIR, os.path.join(ROOT_DIR, "backend")]:
    if path not in sys.path:
        sys.path.insert(0, path)

from backend.app.main import app
