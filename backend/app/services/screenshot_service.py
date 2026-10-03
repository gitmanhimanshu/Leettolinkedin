"""Screenshot validation and processing service."""

import base64
import io
import logging
from typing import Tuple
from PIL import Image

logger = logging.getLogger(__name__)

MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


class ScreenshotService:
    """Validates and processes screenshot payloads from the Chrome extension."""

    def validate_image_payload(self, data_url: str) -> Tuple[bool, str]:
        """
        Validate base64 image data URL and verify image integrity with Pillow.
        Returns: (is_valid, error_message_or_empty)
        """
        if not data_url or not isinstance(data_url, str):
            return False, "Image payload is missing or empty"

        if not (data_url.startswith("data:image/png;base64,") or data_url.startswith("data:image/jpeg;base64,")):
            return False, "Image must be a valid PNG or JPEG base64 data URL"

        try:
            header, base64_data = data_url.split(",", 1)
            raw_bytes = base64.b64decode(base64_data)

            if len(raw_bytes) > MAX_IMAGE_SIZE_BYTES:
                return False, f"Image size exceeds limit of {MAX_IMAGE_SIZE_BYTES // (1024 * 1024)} MB"

            # Verify image integrity with Pillow
            with Image.open(io.BytesIO(raw_bytes)) as img:
                img.verify()
                width, height = img.size
                if width < 100 or height < 100:
                    return False, f"Image dimensions too small ({width}x{height})"

            return True, ""
        except Exception as e:
            logger.error("Screenshot validation failed: %s", e)
            return False, f"Corrupted or invalid image payload: {str(e)}"

    def extract_image_bytes(self, data_url: str) -> bytes:
        """Decode raw image bytes from base64 data URL."""
        _, base64_data = data_url.split(",", 1)
        return base64.b64decode(base64_data)


screenshot_service = ScreenshotService()
