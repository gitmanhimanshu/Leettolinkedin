"""FastAPI entry point for Vercel when root directory is repository root."""

import os
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app.main import app

__all__ = ["app"]

