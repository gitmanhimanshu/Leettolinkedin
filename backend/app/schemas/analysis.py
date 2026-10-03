"""Schemas for AI analysis and LinkedIn post drafting."""

from typing import List, Optional
from pydantic import BaseModel, Field


class GrokAnalysisResult(BaseModel):
    """Structured algorithm analysis schema."""
    problem_title: str = Field(..., description="Title of the problem")
    problem_summary: str = Field(..., description="Concise summary of the challenge")
    algorithmic_approach: str = Field(..., description="Core approach (e.g. Hash Map, Two Pointers)")
    step_by_step_explanation: List[str] = Field(default_factory=list, description="Step-by-step breakdown")
    data_structures: List[str] = Field(default_factory=list, description="Data structures utilized")
    time_complexity: str = Field(..., description="Big-O time complexity with justification")
    space_complexity: str = Field(..., description="Big-O space complexity with justification")
    edge_cases: List[str] = Field(default_factory=list, description="Key edge cases considered")
    linkedin_caption: str = Field(..., description="Engaging, professional LinkedIn post caption")
    hashtags: List[str] = Field(default_factory=list, description="Relevant LinkedIn hashtags")


class AnalyzeSubmissionRequest(BaseModel):
    submission_id: str
    custom_instructions: Optional[str] = None


class PublishPostRequest(BaseModel):
    submission_id: str
    caption: str
    include_image: bool = True
