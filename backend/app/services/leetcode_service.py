"""LeetCode submission detection, normalization, and validation service."""

import logging
from typing import Tuple, Optional, Dict, Any
from backend.app.schemas.submission import (
    SubmissionDetectRequest,
    SubmissionResponse,
    ProcessingState,
)
from backend.app.models.submission import SubmissionModel
from backend.app.repositories.submission_repo import submission_repo

logger = logging.getLogger(__name__)


class LeetCodeService:
    """Service responsible for validating, enriching, and registering LeetCode submissions."""

    def __init__(self, repo=submission_repo):
        self.repo = repo

    def process_detected_submission(
        self, request: SubmissionDetectRequest
    ) -> Tuple[SubmissionResponse, bool]:
        """
        Process a detected submission from the Chrome Extension.
        
        Guarantees:
        - Only processes 'Accepted' status submissions by default.
        - Uses submission_id as idempotency key to prevent duplicates.
        - Preserves exact verified submitted code.
        """
        existing = self.repo.get_by_id(request.submission_id)
        if existing:
            logger.info("Submission %s already exists. Returning cached record.", request.submission_id)
            response_dict = existing.to_dict()
            response_dict["is_duplicate"] = True
            return SubmissionResponse(**response_dict), False

        # Validate Accepted status
        status_clean = request.status_msg.strip().title()
        if status_clean != "Accepted":
            logger.warning(
                "Submission %s status '%s' is not 'Accepted'. Skipping post generation pipeline.",
                request.submission_id,
                request.status_msg,
            )
            model = SubmissionModel(
                submission_id=request.submission_id,
                problem_title=request.problem_title,
                problem_slug=request.problem_slug,
                problem_url=request.problem_url,
                language=request.language.lower(),
                submitted_code=request.submitted_code,
                status_msg=request.status_msg,
                runtime=request.runtime,
                memory=request.memory,
                runtime_percentile=request.runtime_percentile,
                memory_percentile=request.memory_percentile,
                difficulty=request.difficulty,
                state=ProcessingState.FAILED,
            )
            saved = self.repo.save(model)
            return SubmissionResponse(**saved.to_dict(), is_duplicate=False), True

        # Valid Accepted submission
        model = SubmissionModel(
            submission_id=request.submission_id,
            problem_title=request.problem_title,
            problem_slug=request.problem_slug,
            problem_url=request.problem_url,
            language=request.language.lower(),
            submitted_code=request.submitted_code,
            status_msg="Accepted",
            runtime=request.runtime,
            memory=request.memory,
            runtime_percentile=request.runtime_percentile,
            memory_percentile=request.memory_percentile,
            difficulty=request.difficulty,
            state=ProcessingState.ACCEPTED,
        )
        saved = self.repo.save(model)
        logger.info(
            "Registered Accepted submission %s for problem '%s'",
            saved.submission_id,
            saved.problem_title,
        )
        return SubmissionResponse(**saved.to_dict(), is_duplicate=False), True

    def register_manual_submission(
        self,
        problem_title: str,
        problem_slug: str,
        language: str,
        submitted_code: str,
        runtime: Optional[str] = None,
        memory: Optional[str] = None,
        difficulty: Optional[str] = None,
    ) -> SubmissionResponse:
        """Safe fallback to manually register a submission if browser detection fails."""
        import time
        sub_id = f"manual_{int(time.time())}"
        model = SubmissionModel(
            submission_id=sub_id,
            problem_title=problem_title,
            problem_slug=problem_slug,
            problem_url=f"https://leetcode.com/problems/{problem_slug}/",
            language=language.lower(),
            submitted_code=submitted_code,
            status_msg="Accepted",
            runtime=runtime,
            memory=memory,
            difficulty=difficulty,
            state=ProcessingState.ACCEPTED,
        )
        saved = self.repo.save(model)
        return SubmissionResponse(**saved.to_dict(), is_duplicate=False)

    def update_analysis(self, submission_id: str, analysis: Dict[str, Any]) -> Optional[SubmissionModel]:
        """Update submission record with generated AI / fallback analysis."""
        record = self.repo.get_by_id(submission_id)
        if not record:
            return None
        record.ai_analysis = analysis
        record.state = ProcessingState.ANALYZED
        return self.repo.save(record)

    def update_image(self, submission_id: str, image_url: str, public_id: str) -> Optional[SubmissionModel]:
        """Update submission with Cloudinary image reference."""
        record = self.repo.get_by_id(submission_id)
        if not record:
            return None
        record.cloudinary_url = image_url
        record.cloudinary_public_id = public_id
        record.state = ProcessingState.IMAGE_UPLOADED
        return self.repo.save(record)

    def update_linkedin_published(self, submission_id: str, post_id: str, status: str) -> Optional[SubmissionModel]:
        """Update submission when posted to LinkedIn."""
        record = self.repo.get_by_id(submission_id)
        if not record:
            return None
        record.linkedin_post_id = post_id
        record.linkedin_status = status
        record.state = ProcessingState.PUBLISHED if status == "published" else ProcessingState.AWAITING_APPROVAL
        return self.repo.save(record)

    def get_submission(self, submission_id: str) -> Optional[SubmissionResponse]:
        """Fetch submission details by ID."""
        record = self.repo.get_by_id(submission_id)
        if not record:
            return None
        return SubmissionResponse(**record.to_dict())


leetcode_service = LeetCodeService()
