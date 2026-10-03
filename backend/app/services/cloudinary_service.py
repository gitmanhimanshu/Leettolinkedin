"""Cloudinary image upload and management service."""

import logging
from typing import Dict, Any, Optional
import cloudinary
import cloudinary.uploader
from backend.app.config import settings

logger = logging.getLogger(__name__)


class CloudinaryService:
    """Service handling screenshot uploads to Cloudinary."""

    def __init__(self):
        self._configured = False
        self._setup()

    def _setup(self):
        if settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_API_SECRET:
            cloudinary.config(
                cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                api_key=settings.CLOUDINARY_API_KEY,
                api_secret=settings.CLOUDINARY_API_SECRET,
                secure=True,
            )
            self._configured = True
            logger.info("Cloudinary configured for cloud: %s", settings.CLOUDINARY_CLOUD_NAME)
        else:
            logger.warning("Cloudinary credentials incomplete in settings.")

    def upload_screenshot(self, image_data: str, submission_id: str) -> Dict[str, Any]:
        """
        Uploads a base64 data URL or image path to Cloudinary.
        
        Returns:
            Dict containing 'secure_url' and 'public_id'.
        """
        if not self._configured:
            self._setup()

        if not self._configured:
            raise ValueError("Cloudinary is not configured. Please verify credentials in .env")

        try:
            logger.info("Uploading screenshot for submission %s to Cloudinary...", submission_id)
            result = cloudinary.uploader.upload(
                image_data,
                folder="code2linkedin",
                public_id=f"sub_{submission_id}",
                overwrite=True,
                resource_type="image",
            )
            logger.info("Cloudinary upload successful: %s", result.get("secure_url"))
            return {
                "secure_url": result["secure_url"],
                "public_id": result["public_id"],
                "format": result.get("format"),
                "bytes": result.get("bytes"),
            }
        except Exception as e:
            logger.error("Cloudinary upload failed: %s", e)
            raise RuntimeError(f"Cloudinary upload error: {str(e)}") from e


cloudinary_service = CloudinaryService()
