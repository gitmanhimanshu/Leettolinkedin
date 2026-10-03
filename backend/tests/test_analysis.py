"""Tests for Grok analysis service and fallback engine."""

import asyncio
from backend.app.services.grok_service import grok_service
from backend.app.schemas.analysis import GrokAnalysisResult


def test_fallback_analysis_hashmap():
    source_code = """
class Solution:
    def twoSum(self, nums: list[int], target: int) -> list[int]:
        seen = {}
        for i, num in enumerate(nums):
            diff = target - num
            if diff in seen:
                return [seen[diff], i]
            seen[num] = i
        return []
"""
    result = asyncio.run(grok_service.analyze_submission(
        problem_title="Two Sum",
        language="python3",
        source_code=source_code,
        runtime="42 ms",
        memory="17.2 MB",
        difficulty="Easy",
    ))

    assert isinstance(result, GrokAnalysisResult)
    assert result.problem_title == "Two Sum"
    assert "Hash Map" in result.algorithmic_approach
    assert "O(N)" in result.time_complexity
    assert len(result.step_by_step_explanation) >= 2
    assert "Two Sum" in result.linkedin_caption
    assert "#LeetCode" in result.hashtags


def test_fallback_analysis_two_pointers():
    source_code = """
class Solution:
    def isPalindrome(self, s: str) -> bool:
        clean = [c.lower() for c in s if c.isalnum()]
        left, right = 0, len(clean) - 1
        while left < right:
            if clean[left] != clean[right]:
                return False
            left += 1
            right -= 1
        return True
"""
    result = asyncio.run(grok_service.analyze_submission(
        problem_title="Valid Palindrome",
        language="python3",
        source_code=source_code,
        runtime="35 ms",
        memory="18.0 MB",
        difficulty="Easy",
    ))

    assert isinstance(result, GrokAnalysisResult)
    assert "Two Pointers" in result.algorithmic_approach
    assert "#Python3" in result.hashtags
