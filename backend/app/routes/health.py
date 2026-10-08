"""Health check route with public access and diagnostic details."""

from datetime import datetime, timezone
from fastapi import APIRouter
from backend.app.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Public lightweight health check")
@router.get("/api/health", summary="API health status check")
def health_check():
    """Public health status endpoint for monitoring, uptime checks, and Chrome extension."""
    from backend.app.repositories.submission_repo import submission_repo
    mongo_active = submission_repo._mongo_client is not None

    return {
        "status": "healthy",
        "app": "Code2LinkedIn Backend",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "database": "mongodb_connected" if mongo_active else "in_memory_fallback",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
