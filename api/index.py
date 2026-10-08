"""Vercel Serverless Function entry point for FastAPI backend."""

import os
import sys

# Ensure root directory and backend are on Python path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
for path in [ROOT_DIR, os.path.join(ROOT_DIR, "backend")]:
    if path not in sys.path:
        sys.path.insert(0, path)

try:
    from backend.app.main import app
except Exception:
    import traceback
    from fastapi import FastAPI
    from fastapi.responses import PlainTextResponse

    err_trace = traceback.format_exc()
    app = FastAPI()

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
    def error_fallback(path: str = ""):
        return PlainTextResponse(f"FastAPI Startup Error on Vercel:\n\n{err_trace}", status_code=500)
