"""Pydantic schemas for LeetCode submissions and pipeline processing."""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class ProcessingState(str, Enum):
    """Lifecycle states of a submission in the Code2LinkedIn pipeline."""
    DETECTED = "detected"
    ACCEPTED = "accepted"
    ANALYZED = "analyzed"
    IMAGE_UPLOADED = "image_uploaded"
    AWAITING_APPROVAL = "awaiting_approval"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"


class SubmissionDetectRequest(BaseModel):
    """Payload received from the Chrome extension upon detecting a submission."""
    submission_id: str = Field(..., description="Unique LeetCode submission identifier")
    problem_title: str = Field(..., description="Title of the LeetCode problem")
    problem_slug: str = Field(..., description="Slug of the LeetCode problem")
    problem_url: Optional[str] = Field(None, description="Direct URL to the problem")
    language: str = Field(..., description="Programming language used (e.g., python3, cpp)")
    submitted_code: str = Field(..., min_length=1, description="Actual verified submitted source code")
    status_msg: str = Field("Accepted", description="Verdict message from LeetCode")
    runtime: Optional[str] = Field(None, description="Execution runtime (e.g., '45 ms')")
    memory: Optional[str] = Field(None, description="Memory used (e.g., '17.2 MB')")
    runtime_percentile: Optional[float] = Field(None, description="Runtime percentile vs other submissions")
    memory_percentile: Optional[float] = Field(None, description="Memory percentile vs other submissions")
    difficulty: Optional[str] = Field(None, description="Problem difficulty (Easy, Medium, Hard)")
    timestamp: Optional[int] = Field(None, description="Epoch timestamp of submission detection")


class SubmissionResponse(BaseModel):
    """Standard response model for submission queries."""
    submission_id: str
    problem_title: str
    problem_slug: str
    problem_url: Optional[str] = None
    language: str
    submitted_code: str
    status_msg: str
    runtime: Optional[str] = None
    memory: Optional[str] = None
    runtime_percentile: Optional[float] = None
    memory_percentile: Optional[float] = None
    difficulty: Optional[str] = None
    state: ProcessingState
    created_at: datetime
    updated_at: datetime
    ai_analysis: Optional[Dict[str, Any]] = None
    cloudinary_url: Optional[str] = None
    cloudinary_public_id: Optional[str] = None
    linkedin_post_id: Optional[str] = None
    linkedin_status: Optional[str] = None
    is_duplicate: bool = False
