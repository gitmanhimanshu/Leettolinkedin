"""Official LinkedIn OAuth 2.0, Images API, and Posts API integration service."""

import logging
import urllib.parse
from typing import Optional, Dict, Any, Tuple
import httpx
from backend.app.config import settings

logger = logging.getLogger(__name__)

LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
LINKEDIN_IMAGES_API = "https://api.linkedin.com/rest/images?action=initializeUpload"
LINKEDIN_POSTS_API = "https://api.linkedin.com/rest/posts"
LINKEDIN_API_VERSION = "202401"


class LinkedInService:
    """Handles OAuth 2.0 authorization, member identity, image upload, and posting to LinkedIn."""

    def __init__(self):
        self.client_id = settings.LINKEDIN_CLIENT_ID
        self.client_secret = settings.LINKEDIN_CLIENT_SECRET
        self.redirect_uri = settings.LINKEDIN_REDIRECT_URI
        self.scope = settings.LINKEDIN_SCOPE
        # Stored active credentials
        self._access_token: Optional[str] = None
        self._member_urn: Optional[str] = None
        self._member_name: Optional[str] = None

    def _ensure_auth_loaded(self):
        """Load auth tokens from persistent storage if not already in memory."""
        if not self._access_token:
            from backend.app.repositories.submission_repo import submission_repo
            cached = submission_repo.get_auth("linkedin")
            if cached and isinstance(cached, dict):
                self._access_token = cached.get("access_token")
                self._member_urn = cached.get("member_urn")
                self._member_name = cached.get("member_name")

    def is_configured(self) -> bool:
        """Check if client ID and secret are set."""
        return bool(self.client_id and self.client_secret)

    def is_authorized(self) -> bool:
        """Check if user has an active access token."""
        self._ensure_auth_loaded()
        return bool(self._access_token and self._member_urn)

    def get_auth_url(self, state: str = "c2l_oauth_state") -> str:
        """Construct LinkedIn OAuth 2.0 authorization URL."""
        if not self.is_configured():
            raise ValueError("LinkedIn client ID and secret must be configured in .env")

        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
            "scope": self.scope,
        }
        return f"{LINKEDIN_AUTH_URL}?{urllib.parse.urlencode(params)}"

    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token and fetch member identity."""
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            res = await client.post(LINKEDIN_TOKEN_URL, data=data)
            if not res.is_success:
                logger.error("Token exchange failed: %s - %s", res.status_code, res.text)
                raise RuntimeError(f"LinkedIn token exchange failed: {res.text}")

            token_data = res.json()
            access_token = token_data.get("access_token")
            self._access_token = access_token

            # Fetch authenticated member identity (author URN)
            member_urn, member_name = await self._fetch_member_urn(access_token)
            self._member_urn = member_urn
            self._member_name = member_name

            logger.info("LinkedIn authorized successfully for member %s (%s)", member_name, member_urn)

            # Persist across serverless invocations
            from backend.app.repositories.submission_repo import submission_repo
            submission_repo.save_auth("linkedin", {
                "access_token": access_token,
                "expires_in": token_data.get("expires_in"),
                "member_urn": member_urn,
                "member_name": member_name,
            })

            return {
                "access_token": access_token,
                "expires_in": token_data.get("expires_in"),
                "member_urn": member_urn,
                "member_name": member_name,
            }

    async def _fetch_member_urn(self, access_token: str) -> Tuple[str, str]:
        """Retrieve member's Person URN using OpenID UserInfo endpoint."""
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.get(LINKEDIN_USERINFO_URL, headers=headers)
            if not res.is_success:
                raise RuntimeError(f"Failed to fetch LinkedIn user info: {res.text}")

            data = res.json()
            sub = data.get("sub")
            name = data.get("name", "LinkedIn Member")

            if not sub:
                raise ValueError("Could not extract member identifier ('sub') from userinfo")

            member_urn = f"urn:li:person:{sub}"
            return member_urn, name

    def _get_headers(self, version: Optional[str] = None) -> Dict[str, str]:
        ver = version or getattr(settings, "LINKEDIN_API_VERSION", "202601")
        return {
            "Authorization": f"Bearer {self._access_token}",
            "LinkedIn-Version": ver,
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        }

    async def _post_with_version_fallback(
        self,
        client: httpx.AsyncClient,
        url: str,
        json_body: Dict[str, Any],
    ) -> httpx.Response:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        current_ym = f"{now.year}{now.month:02d}"
        prev_month = 12 if now.month == 1 else now.month - 1
        prev_year = now.year - 1 if now.month == 1 else now.year
        prev_ym = f"{prev_year}{prev_month:02d}"

        configured_ver = getattr(settings, "LINKEDIN_API_VERSION", "202601")
        versions_to_try = [
            configured_ver,
            prev_ym,
            current_ym,
            "202601",
            "202602",
            "202606",
            "202512",
        ]
        unique_versions = list(dict.fromkeys(v for v in versions_to_try if v))

        last_res = None
        for ver in unique_versions:
            headers = self._get_headers(version=ver)
            res = await client.post(url, headers=headers, json=json_body)
            if res.status_code != 426 and "NONEXISTENT_VERSION" not in res.text:
                return res
            logger.warning("LinkedIn version %s rejected with 426. Trying next candidate...", ver)
            last_res = res
        return last_res

    async def upload_image_to_linkedin(self, image_bytes: bytes) -> str:
        """
        Uploads image directly to LinkedIn using official 2-step Images API.
        Returns: urn:li:image:...
        """
        if not self.is_authorized():
            raise RuntimeError("LinkedIn account is not authorized. Please authenticate first.")

        init_payload = {
            "initializeUploadRequest": {
                "owner": self._member_urn
            }
        }

        # Step 1: Initialize Upload
        async with httpx.AsyncClient(timeout=30.0) as client:
            init_res = await self._post_with_version_fallback(client, LINKEDIN_IMAGES_API, init_payload)
            if not init_res.is_success:
                raise RuntimeError(f"Failed to initialize LinkedIn image upload: {init_res.text}")

            init_data = init_res.json()
            upload_url = init_data["value"]["uploadUrl"]
            image_urn = init_data["value"]["image"]

            # Step 2: Upload raw image binary
            upload_headers = {"Content-Type": "image/png"}
            put_res = await client.put(upload_url, headers=upload_headers, content=image_bytes)
            if not put_res.is_success:
                raise RuntimeError(f"Failed to upload image bytes to LinkedIn: {put_res.text}")

            logger.info("Image uploaded to LinkedIn with URN: %s", image_urn)
            return image_urn

    async def publish_post(
        self,
        caption: str,
        image_bytes: Optional[bytes] = None,
        title: str = "LeetCode Solution",
    ) -> Dict[str, Any]:
        """
        Publish post with optional image to LinkedIn using official Posts API.
        Respects LINKEDIN_DRAFT_MODE if enabled.
        """
        if settings.LINKEDIN_DRAFT_MODE:
            import time
            logger.info("LINKEDIN_DRAFT_MODE is active. Skipping live publish.")
            return {
                "status": "draft_saved",
                "post_id": f"draft_{int(time.time())}",
                "message": "Draft saved successfully (Draft mode is enabled in config).",
                "author": self._member_urn or "urn:li:person:draft_member",
                "caption": caption,
            }

        if not self.is_authorized():
            raise RuntimeError("LinkedIn account is not connected. Please log in via OAuth first.")

        # Upload image if provided
        media_payload = None
        if image_bytes:
            image_urn = await self.upload_image_to_linkedin(image_bytes)
            media_payload = {
                "title": title,
                "id": image_urn,
            }

        post_body = {
            "author": self._member_urn,
            "commentary": caption,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }

        if media_payload:
            post_body["content"] = {"media": media_payload}

        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await self._post_with_version_fallback(client, LINKEDIN_POSTS_API, post_body)
            if not res.is_success:
                logger.error("Failed to publish post: %s - %s", res.status_code, res.text)
                raise RuntimeError(f"LinkedIn publish error: {res.text}")

            post_urn = res.headers.get("x-restli-id", "urn:li:share:published")
            logger.info("Successfully published post to LinkedIn: %s", post_urn)
            return {
                "status": "published",
                "post_id": post_urn,
                "author": self._member_urn,
                "message": "Successfully published to LinkedIn feed!",
            }


linkedin_service = LinkedInService()
