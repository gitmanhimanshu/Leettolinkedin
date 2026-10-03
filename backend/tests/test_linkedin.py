"""Tests for LinkedIn service and API routes."""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.leetcode_service import leetcode_service
from backend.app.config import settings

client = TestClient(app)


def test_linkedin_status_endpoint():
    response = client.get("/api/auth/linkedin/status")
    assert response.status_code == 200
    data = response.json()
    assert "configured" in data
    assert "authorized" in data
    assert data["configured"] is True


def test_linkedin_login_redirect():
    response = client.get("/api/auth/linkedin/login", follow_redirects=False)
    assert response.status_code in (302, 307)
    location = response.headers.get("location", "")
    assert "linkedin.com/oauth/v2/authorization" in location
    assert settings.LINKEDIN_CLIENT_ID in location


def test_linkedin_publish_draft_mode(monkeypatch):
    # Ensure draft mode is active for safe test execution
    monkeypatch.setattr(settings, "LINKEDIN_DRAFT_MODE", True)

    # Register a test submission
    sub = leetcode_service.register_manual_submission(
        problem_title="Merge Two Sorted Lists",
        problem_slug="merge-two-sorted-lists",
        language="python3",
        submitted_code="class Solution: def mergeTwoLists(...): pass",
    )

    payload = {
        "submission_id": sub.submission_id,
        "caption": "Just solved Merge Two Sorted Lists! 🚀",
        "include_image": False,
    }

    response = client.post("/api/linkedin/publish", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "draft_saved"
    assert "Draft saved successfully" in data["message"]
