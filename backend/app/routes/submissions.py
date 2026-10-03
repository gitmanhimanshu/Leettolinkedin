"""Submissions API endpoints including detection, manual fallback, analysis, and screenshot upload."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.app.schemas.submission import (
    SubmissionDetectRequest,
    SubmissionResponse,
)
from backend.app.schemas.analysis import (
    GrokAnalysisResult,
    AnalyzeSubmissionRequest,
)
from backend.app.services.leetcode_service import leetcode_service
from backend.app.services.grok_service import grok_service
from backend.app.services.screenshot_service import screenshot_service
from backend.app.services.cloudinary_service import cloudinary_service
from backend.app.repositories.submission_repo import submission_repo

router = APIRouter(prefix="/api/submissions", tags=["Submissions"])


class ManualSubmissionRequest(BaseModel):
    problem_title: str
    problem_slug: str
    language: str
    submitted_code: str
    runtime: Optional[str] = None
    memory: Optional[str] = None
    difficulty: Optional[str] = None


class UploadScreenshotRequest(BaseModel):
    submission_id: str
    image_data: str = Field(..., description="Base64 data URL of the screenshot")


@router.post(
    "/detect",
    response_model=SubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register newly detected submission from Chrome Extension",
)
def detect_submission(payload: SubmissionDetectRequest):
    """
    Receives submission data detected by the Chrome extension.
    - Idempotent: Subsequent calls with the same submission_id return existing record.
    - Status filtering: Non-accepted submissions are recorded but not processed further.
    """
    response, is_new = leetcode_service.process_detected_submission(payload)
    return response


@router.post(
    "/manual",
    response_model=SubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Manual fallback submission registration",
)
def manual_submission(payload: ManualSubmissionRequest):
    """Fallback endpoint when automated browser extraction is unavailable or skipped."""
    return leetcode_service.register_manual_submission(
        problem_title=payload.problem_title,
        problem_slug=payload.problem_slug,
        language=payload.language,
        submitted_code=payload.submitted_code,
        runtime=payload.runtime,
        memory=payload.memory,
        difficulty=payload.difficulty,
    )


@router.post(
    "/analyze",
    response_model=GrokAnalysisResult,
    summary="Analyze code and generate LinkedIn caption via Grok or fallback engine",
)
async def analyze_submission(payload: AnalyzeSubmissionRequest):
    """Analyzes verified code using xAI Grok (or intelligent rule-based engine when API key is not set)."""
    record = leetcode_service.get_submission(payload.submission_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Submission {payload.submission_id} not found",
        )

    analysis = await grok_service.analyze_submission(
        problem_title=record.problem_title,
        language=record.language,
        source_code=record.submitted_code,
        runtime=record.runtime,
        memory=record.memory,
        difficulty=record.difficulty,
    )

    # Save generated analysis into submission record
    leetcode_service.update_analysis(payload.submission_id, analysis.model_dump())
    return analysis


@router.post(
    "/upload-screenshot",
    summary="Upload screenshot to Cloudinary and link to submission",
)
def upload_screenshot(payload: UploadScreenshotRequest):
    """Validates image data URL with Pillow and uploads directly to Cloudinary."""
    is_valid, error_msg = screenshot_service.validate_image_payload(payload.image_data)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid screenshot payload: {error_msg}",
        )

    try:
        upload_result = cloudinary_service.upload_screenshot(
            payload.image_data, payload.submission_id
        )
        leetcode_service.update_image(
            payload.submission_id,
            upload_result["secure_url"],
            upload_result["public_id"],
        )
        return {
            "status": "success",
            "submission_id": payload.submission_id,
            "cloudinary_url": upload_result["secure_url"],
            "public_id": upload_result["public_id"],
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload to Cloudinary: {str(e)}",
        )


@router.get(
    "",
    response_model=List[SubmissionResponse],
    summary="List recent submissions",
)
def list_submissions(limit: int = 50):
    """Retrieve history of detected submissions."""
    records = submission_repo.list_all(limit=limit)
    return [SubmissionResponse(**r.to_dict()) for r in records]


@router.get(
    "/{submission_id}",
    response_model=SubmissionResponse,
    summary="Get single submission by submission ID",
)
def get_submission(submission_id: str):
    """Fetch details of a single submission."""
    record = leetcode_service.get_submission(submission_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Submission {submission_id} not found",
        )
    return record
