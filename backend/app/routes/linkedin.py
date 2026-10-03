"""LinkedIn OAuth 2.0 authorization and publication routes."""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse
import httpx
from pydantic import BaseModel

from backend.app.services.linkedin_service import linkedin_service
from backend.app.services.leetcode_service import leetcode_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/linkedin", tags=["LinkedIn"])
auth_router = APIRouter(prefix="/api/auth/linkedin", tags=["LinkedIn Auth"])


class PublishRequest(BaseModel):
    submission_id: str
    caption: str
    include_image: bool = True


@auth_router.get("/status", summary="Check LinkedIn OAuth authorization status")
def get_linkedin_status():
    """Returns current LinkedIn authentication status and member name if active."""
    return {
        "configured": linkedin_service.is_configured(),
        "authorized": linkedin_service.is_authorized(),
        "member_name": linkedin_service._member_name,
        "member_urn": linkedin_service._member_urn,
    }


@auth_router.get("/login", summary="Initiate LinkedIn OAuth 2.0 flow")
def linkedin_login():
    """Redirects user to LinkedIn authorization page."""
    if not linkedin_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="LinkedIn client ID and secret must be configured in .env",
        )
    auth_url = linkedin_service.get_auth_url()
    return RedirectResponse(auth_url)


@auth_router.get("/callback", response_class=HTMLResponse, summary="LinkedIn OAuth callback handler")
async def linkedin_callback(code: Optional[str] = None, error: Optional[str] = None, error_description: Optional[str] = None):
    """Handles OAuth authorization code callback from LinkedIn."""
    if error:
        logger.error("LinkedIn OAuth error: %s - %s", error, error_description)
        return HTMLResponse(
            content=f"""
            <html>
                <body style="font-family: sans-serif; background: #0f172a; color: #f8fafc; padding: 40px; text-align: center;">
                    <h2 style="color: #ef4444;">LinkedIn Authorization Failed</h2>
                    <p>{error}: {error_description}</p>
                    <p>Please check your application permissions in LinkedIn Developer Portal.</p>
                </body>
            </html>
            """,
            status_code=400,
        )

    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    try:
        result = await linkedin_service.exchange_code_for_token(code)
        member_name = result.get("member_name", "Member")
        return HTMLResponse(
            content=f"""
            <html>
                <head><title>Code2LinkedIn - Connected</title></head>
                <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0;">
                    <div style="background: #1e293b; padding: 32px 48px; border-radius: 12px; border: 1px solid #334155; text-align: center; max-width: 480px; box-shadow: 0 10px 25px rgba(0,0,0,0.5);">
                        <div style="font-size: 48px; margin-bottom: 12px;">🎉</div>
                        <h2 style="margin: 0 0 8px 0; color: #38bdf8;">Connected to LinkedIn!</h2>
                        <p style="color: #94a3b8; font-size: 14px; margin-bottom: 20px;">
                            Successfully authenticated as <strong>{member_name}</strong>.
                        </p>
                        <p style="color: #cbd5e1; font-size: 13px;">
                            You can close this tab and return to the Chrome Extension to preview and publish your post.
                        </p>
                    </div>
                </body>
            </html>
            """
        )
    except Exception as e:
        logger.error("Callback exception: %s", e)
        return HTMLResponse(
            content=f"""
            <html>
                <body style="font-family: sans-serif; background: #0f172a; color: #f8fafc; padding: 40px; text-align: center;">
                    <h2 style="color: #ef4444;">Authorization Exchange Error</h2>
                    <p>{str(e)}</p>
                </body>
            </html>
            """,
            status_code=500,
        )


@router.post("/publish", summary="Publish post to LinkedIn with screenshot")
async def publish_to_linkedin(payload: PublishRequest):
    """Publishes a LeetCode solution post with caption and screenshot to LinkedIn."""
    record = leetcode_service.get_submission(payload.submission_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Submission {payload.submission_id} not found",
        )

    # Optional image download from Cloudinary if included
    image_bytes = None
    if payload.include_image and record.cloudinary_url:
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                img_res = await client.get(record.cloudinary_url)
                if img_res.is_success:
                    image_bytes = img_res.content
        except Exception as e:
            logger.warning("Could not download Cloudinary image for LinkedIn attachment: %s", e)

    try:
        result = await linkedin_service.publish_post(
            caption=payload.caption,
            image_bytes=image_bytes,
            title=f"Solution for {record.problem_title}",
        )
        # Update submission record in database
        leetcode_service.update_linkedin_published(
            payload.submission_id,
            post_id=result.get("post_id", "published"),
            status=result.get("status", "published"),
        )
        return result
    except Exception as e:
        logger.error("LinkedIn publish failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to publish post to LinkedIn: {str(e)}",
        )
