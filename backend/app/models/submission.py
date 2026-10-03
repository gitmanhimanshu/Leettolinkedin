"""Data model for submissions."""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from backend.app.schemas.submission import ProcessingState


@dataclass
class SubmissionModel:
    """Internal representation of a LeetCode submission entity."""
    submission_id: str
    problem_title: str
    problem_slug: str
    language: str
    submitted_code: str
    status_msg: str = "Accepted"
    problem_url: Optional[str] = None
    runtime: Optional[str] = None
    memory: Optional[str] = None
    runtime_percentile: Optional[float] = None
    memory_percentile: Optional[float] = None
    difficulty: Optional[str] = None
    state: ProcessingState = ProcessingState.DETECTED
    ai_analysis: Optional[Dict[str, Any]] = None
    cloudinary_url: Optional[str] = None
    cloudinary_public_id: Optional[str] = None
    linkedin_post_id: Optional[str] = None
    linkedin_status: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for MongoDB persistence or response serialization."""
        return {
            "submission_id": self.submission_id,
            "problem_title": self.problem_title,
            "problem_slug": self.problem_slug,
            "problem_url": self.problem_url,
            "language": self.language,
            "submitted_code": self.submitted_code,
            "status_msg": self.status_msg,
            "runtime": self.runtime,
            "memory": self.memory,
            "runtime_percentile": self.runtime_percentile,
            "memory_percentile": self.memory_percentile,
            "difficulty": self.difficulty,
            "state": self.state.value if isinstance(self.state, ProcessingState) else self.state,
            "ai_analysis": self.ai_analysis,
            "cloudinary_url": self.cloudinary_url,
            "cloudinary_public_id": self.cloudinary_public_id,
            "linkedin_post_id": self.linkedin_post_id,
            "linkedin_status": self.linkedin_status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SubmissionModel":
        """Instantiate model from dictionary."""
        return cls(
            submission_id=data["submission_id"],
            problem_title=data.get("problem_title", ""),
            problem_slug=data.get("problem_slug", ""),
            problem_url=data.get("problem_url"),
            language=data.get("language", ""),
            submitted_code=data.get("submitted_code", ""),
            status_msg=data.get("status_msg", "Accepted"),
            runtime=data.get("runtime"),
            memory=data.get("memory"),
            runtime_percentile=data.get("runtime_percentile"),
            memory_percentile=data.get("memory_percentile"),
            difficulty=data.get("difficulty"),
            state=ProcessingState(data.get("state", ProcessingState.DETECTED)),
            ai_analysis=data.get("ai_analysis"),
            cloudinary_url=data.get("cloudinary_url"),
            cloudinary_public_id=data.get("cloudinary_public_id"),
            linkedin_post_id=data.get("linkedin_post_id"),
            linkedin_status=data.get("linkedin_status"),
            created_at=data.get("created_at", datetime.now(timezone.utc)),
            updated_at=data.get("updated_at", datetime.now(timezone.utc)),
        )
