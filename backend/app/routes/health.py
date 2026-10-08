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
    col = submission_repo._get_collection()
    mongo_active = col is not None

    return {
        "status": "healthy",
        "app": "Code2LinkedIn Backend",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "database": "mongodb_connected" if mongo_active else "in_memory_fallback",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/keep-alive", summary="Read/Write heartbeat for UptimeRobot to keep DB awake")
@router.get("/api/keep-alive", summary="API Read/Write heartbeat for UptimeRobot")
@router.post("/api/keep-alive", summary="POST Read/Write heartbeat for UptimeRobot")
def keep_alive():
    """
    Dedicated endpoint for UptimeRobot / cron-job pings.
    Performs an active write + read against MongoDB Atlas, preventing
    the free-tier cluster from pausing or falling asleep.
    """
    from backend.app.repositories.submission_repo import submission_repo
    result = submission_repo.ping_and_keepalive()
    return {
        "status": "awake",
        "app": "Code2LinkedIn Backend",
        "environment": settings.ENVIRONMENT,
        "keepalive": result,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
