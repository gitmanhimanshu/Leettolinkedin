from .health import router as health_router
from .submissions import router as submissions_router
from .linkedin import router as linkedin_router, auth_router as linkedin_auth_router

__all__ = ["health_router", "submissions_router", "linkedin_router", "linkedin_auth_router"]
