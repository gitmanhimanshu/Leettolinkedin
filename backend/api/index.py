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
    try:
        from backend.app.main import app
    except ImportError:
        from app.main import app
except Exception:
    import traceback
    from fastapi import FastAPI
    from fastapi.responses import PlainTextResponse

    err_trace = traceback.format_exc()
    app = FastAPI()

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
    def error_fallback(path: str = ""):
        return PlainTextResponse(f"FastAPI Startup Error on Vercel:\n\n{err_trace}", status_code=500)
