"""Vercel Serverless Function entry point for FastAPI backend with diagnostic fallback."""

import os
import sys
import traceback

# Ensure root directory is on Python path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

try:
    from backend.app.main import app
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
