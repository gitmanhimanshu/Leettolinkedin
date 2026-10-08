"""Vercel entry point if root directory is configured as backend/."""

import os
import sys
import traceback

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
ROOT_DIR = os.path.dirname(BACKEND_DIR)

for p in [BACKEND_DIR, ROOT_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    try:
        from backend.app.main import app
    except ImportError:
        from app.main import app
except Exception as e:
    err_str = traceback.format_exc()
    from fastapi import FastAPI
    from fastapi.responses import PlainTextResponse
    app = FastAPI(title="Error Diagnostic")

    @app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
    async def catch_all(path_name: str):
        return PlainTextResponse(f"FastAPI Startup Error:\n\n{err_str}", status_code=500)

try:
    from mangum import Mangum
    handler = Mangum(app)
except Exception:
    handler = app

__all__ = ["app", "handler"]
