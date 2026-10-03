"""Health check route."""

from fastapi import APIRouter
from backend.app.config import settings

router = APIRouter(prefix="/api/health", tags=["Health"])


@router.get("")
def health_check():
    """Health status endpoint for Chrome extension and monitoring."""
    return {
        "status": "healthy",
        "app": "Code2LinkedIn Backend",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
    }
