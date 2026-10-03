"""Tests for screenshot validation service."""

import base64
import io
from PIL import Image
from backend.app.services.screenshot_service import screenshot_service


def _generate_test_image_data_url(width: int = 200, height: int = 200) -> str:
    img = Image.new("RGB", (width, height), color=(20, 30, 40))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    raw_bytes = buffer.getvalue()
    b64_str = base64.b64encode(raw_bytes).decode("utf-8")
    return f"data:image/png;base64,{b64_str}"


def test_valid_screenshot_payload():
    data_url = _generate_test_image_data_url(300, 200)
    is_valid, err = screenshot_service.validate_image_payload(data_url)
    assert is_valid is True
    assert err == ""


def test_invalid_screenshot_corrupted():
    corrupted_data_url = "data:image/png;base64,invalidcorruptedbase64=="
    is_valid, err = screenshot_service.validate_image_payload(corrupted_data_url)
    assert is_valid is False
    assert "Corrupted" in err or "failed" in err.lower()


def test_invalid_screenshot_non_image():
    is_valid, err = screenshot_service.validate_image_payload("not-a-data-url")
    assert is_valid is False
