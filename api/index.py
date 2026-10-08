"""Vercel Serverless Function entry point for FastAPI backend."""

import os
import sys

# Add project root directory to Python path for module resolution
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app.main import app

# Export app for Vercel's ASGI runtime
__all__ = ["app"]
