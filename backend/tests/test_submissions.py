"""Tests for submission detection, idempotency, and retrieval."""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.repositories.submission_repo import submission_repo
from backend.app.schemas.submission import ProcessingState

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_repo():
    """Ensure in-memory repository is cleared before each test."""
    submission_repo.clear()
    yield
    submission_repo.clear()


def test_detect_accepted_submission():
    payload = {
        "submission_id": "11451401",
        "problem_title": "Two Sum",
        "problem_slug": "two-sum",
        "problem_url": "https://leetcode.com/problems/two-sum/",
        "language": "python3",
        "submitted_code": "class Solution:\n    def twoSum(self, nums, target):\n        lookup = {}\n        for i, n in enumerate(nums):\n            diff = target - n\n            if diff in lookup:\n                return [lookup[diff], i]\n            lookup[n] = i",
        "status_msg": "Accepted",
        "runtime": "48 ms",
        "memory": "17.6 MB",
        "runtime_percentile": 82.5,
        "memory_percentile": 65.3,
        "difficulty": "Easy",
        "timestamp": 1727952000,
    }

    response = client.post("/api/submissions/detect", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["submission_id"] == "11451401"
    assert data["problem_title"] == "Two Sum"
    assert data["state"] == ProcessingState.ACCEPTED.value
    assert data["is_duplicate"] is False
    assert "class Solution" in data["submitted_code"]


def test_idempotent_duplicate_submission():
    payload = {
        "submission_id": "11451402",
        "problem_title": "Valid Anagram",
        "problem_slug": "valid-anagram",
        "language": "python3",
        "submitted_code": "class Solution: def isAnagram(self, s, t): return Counter(s) == Counter(t)",
        "status_msg": "Accepted",
    }

    # First call
    res1 = client.post("/api/submissions/detect", json=payload)
    assert res1.status_code == 201
    assert res1.json()["is_duplicate"] is False

    # Second call with identical submission_id
    res2 = client.post("/api/submissions/detect", json=payload)
    assert res2.status_code == 201
    assert res2.json()["is_duplicate"] is True
    assert res2.json()["submission_id"] == "11451402"


def test_reject_or_flag_non_accepted_submission():
    payload = {
        "submission_id": "11451403",
        "problem_title": "Median of Two Sorted Arrays",
        "problem_slug": "median-of-two-sorted-arrays",
        "language": "cpp",
        "submitted_code": "class Solution { public: double findMedianSortedArrays(...) {} };",
        "status_msg": "Wrong Answer",
    }

    response = client.post("/api/submissions/detect", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["submission_id"] == "11451403"
    # Status is marked FAILED / not accepted for posting
    assert data["state"] == ProcessingState.FAILED.value
    assert data["status_msg"] == "Wrong Answer"


def test_validation_missing_code():
    payload = {
        "submission_id": "11451404",
        "problem_title": "Missing Code",
        "problem_slug": "missing-code",
        "language": "python3",
        "submitted_code": "",  # Empty code must fail validation
        "status_msg": "Accepted",
    }

    response = client.post("/api/submissions/detect", json=payload)
    assert response.status_code == 422


def test_get_submission_by_id():
    payload = {
        "submission_id": "11451405",
        "problem_title": "Climbing Stairs",
        "problem_slug": "climbing-stairs",
        "language": "python3",
        "submitted_code": "class Solution: def climbStairs(self, n): return n",
        "status_msg": "Accepted",
    }
    client.post("/api/submissions/detect", json=payload)

    # Fetch existing
    res_get = client.get("/api/submissions/11451405")
    assert res_get.status_code == 200
    assert res_get.json()["submission_id"] == "11451405"

    # Fetch non-existing
    res_404 = client.get("/api/submissions/99999999")
    assert res_404.status_code == 404


def test_list_submissions():
    # Insert two submissions
    for idx in range(1, 3):
        client.post(
            "/api/submissions/detect",
            json={
                "submission_id": f"sub_{idx}",
                "problem_title": f"Problem {idx}",
                "problem_slug": f"problem-{idx}",
                "language": "python3",
                "submitted_code": f"# Code {idx}",
                "status_msg": "Accepted",
            },
        )

    res = client.get("/api/submissions")
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 2
