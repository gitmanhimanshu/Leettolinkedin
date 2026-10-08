"""FastAPI application entry point for Code2LinkedIn backend."""

import logging
import os
import sys
import types

# Ensure 'backend' module is always aliasable even when root is backend/
if "backend" not in sys.modules:
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    backend_pkg = types.ModuleType("backend")
    backend_pkg.__path__ = [backend_dir]
    sys.modules["backend"] = backend_pkg
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import settings
from backend.app.routes import (
    health_router,
    submissions_router,
    linkedin_router,
    linkedin_auth_router,
)

# Configure structured logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("code2linkedin")

# Initialize FastAPI without blocking lifespan for serverless / Vercel compatibility
app = FastAPI(
    title="Code2LinkedIn API",
    description="Backend orchestration service for automated LeetCode submission extraction and LinkedIn sharing.",
    version="1.0.0",
)

# CORS Middleware to allow requests from Chrome Extension, localhost, and Vercel
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routes
app.include_router(health_router)
app.include_router(submissions_router)
app.include_router(linkedin_auth_router)
app.include_router(linkedin_router)


@app.get("/", tags=["Root"])
def root():
    """Root info endpoint."""
    return {
        "project": "Code2LinkedIn",
        "description": "Automated LeetCode-to-LinkedIn AI Agent Backend",
        "status": "online",
        "health_check": "/health",
        "docs_url": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
