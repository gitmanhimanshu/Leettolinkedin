"""FastAPI entry point for Vercel when root directory is backend."""

import os
import sys
import types

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

# Alias 'backend' module so imports like `from backend.app...` work seamlessly
if "backend" not in sys.modules:
    backend_pkg = types.ModuleType("backend")
    backend_pkg.__path__ = [CURRENT_DIR]
    sys.modules["backend"] = backend_pkg

from app.main import app

__all__ = ["app"]

