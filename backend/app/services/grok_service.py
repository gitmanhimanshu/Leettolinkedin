"""xAI Grok analysis service with intelligent rule-based fallback."""

import json
import logging
import re
from typing import Optional, List
import httpx
from backend.app.config import settings
from backend.app.schemas.analysis import GrokAnalysisResult

logger = logging.getLogger(__name__)


class GrokService:
    """Service for analyzing algorithmic source code using xAI Grok API or rule-based fallback."""

    def __init__(self):
        self.api_key = settings.XAI_API_KEY
        self.model = settings.GROK_MODEL
        self.base_url = settings.XAI_BASE_URL.rstrip("/")

    async def analyze_submission(
        self,
        problem_title: str,
        language: str,
        source_code: str,
        runtime: Optional[str] = None,
        memory: Optional[str] = None,
        difficulty: Optional[str] = None,
    ) -> GrokAnalysisResult:
        """
        Analyze verified submitted source code and generate structured LinkedIn content.
        Uses xAI Grok when API key is configured; seamlessly falls back to rule-based engine.
        """
        if self.api_key and self.api_key.strip():
            try:
                logger.info("Attempting xAI Grok analysis with model: %s", self.model)
                return await self._call_grok_api(
                    problem_title, language, source_code, runtime, memory, difficulty
                )
            except Exception as e:
                logger.warning(
                    "xAI Grok API call failed (%s). Falling back to internal analysis engine.", str(e)
                )

        # Fallback analysis
        logger.info("Generating analysis using internal rule-based engine.")
        return self._generate_fallback_analysis(
            problem_title, language, source_code, runtime, memory, difficulty
        )

    async def _call_grok_api(
        self,
        problem_title: str,
        language: str,
        source_code: str,
        runtime: Optional[str],
        memory: Optional[str],
        difficulty: Optional[str],
    ) -> GrokAnalysisResult:
        """Execute request to xAI Grok API."""
        prompt = f"""You are a senior algorithms engineer. Analyze the following Accepted LeetCode solution.
Problem Title: {problem_title}
Difficulty: {difficulty or 'N/A'}
Language: {language}
Reported Runtime: {runtime or 'N/A'}
Reported Memory: {memory or 'N/A'}

Source Code:
```{language}
{source_code}
```

Return ONLY a valid JSON object matching this schema:
{{
  "problem_title": "{problem_title}",
  "problem_summary": "1-2 sentence summary of the problem requirements",
  "algorithmic_approach": "Core algorithmic pattern (e.g. Two Pointers, Hash Table, Sliding Window, DP)",
  "step_by_step_explanation": ["Step 1", "Step 2", "Step 3"],
  "data_structures": ["Data structure 1", "Data structure 2"],
  "time_complexity": "O(...) with 1-sentence reasoning based on code",
  "space_complexity": "O(...) with 1-sentence reasoning based on code",
  "edge_cases": ["Edge case 1", "Edge case 2"],
  "linkedin_caption": "Engaging professional LinkedIn post with clean structure, bullet points, and key takeaway",
  "hashtags": ["#LeetCode", "#Algorithms", "#{language.capitalize()}"]
}}
"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a concise, accurate algorithmic analysis agent. Output ONLY raw JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()

            # Clean markdown JSON fences if returned
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?\s*", "", content)
                content = re.sub(r"\s*```$", "", content)

            parsed = json.loads(content)
            return GrokAnalysisResult(**parsed)

    def _generate_fallback_analysis(
        self,
        problem_title: str,
        language: str,
        source_code: str,
        runtime: Optional[str],
        memory: Optional[str],
        difficulty: Optional[str],
    ) -> GrokAnalysisResult:
        """Deterministic rule-based analysis based on code inspection and metrics."""
        code_lower = source_code.lower()

        # Heuristics for algorithmic approach
        approaches: List[str] = []
        data_structures: List[str] = []
        time_complexity = "O(N)"
        space_complexity = "O(1)"

        if any(kw in code_lower for kw in ["dict(", "{}", "hashmap", "unordered_map", "map<", "lookup", "seen"]):
            approaches.append("Hash Map / Frequency Counter")
            data_structures.append("Hash Table")
            time_complexity = "O(N) — single pass with constant time lookups"
            space_complexity = "O(N) — auxiliary storage for keys"

        if any(kw in code_lower for kw in ["left < right", "low <= high", "left, right", "two pointer", "ptr"]):
            approaches.append("Two Pointers / Binary Search")
            if "mid" in code_lower or "binary" in code_lower:
                time_complexity = "O(log N) — logarithmic search space reduction"
            else:
                time_complexity = "O(N) — linear scan using converging pointers"

        if any(kw in code_lower for kw in ["heapq", "priorityqueue", "priority_queue"]):
            approaches.append("Priority Queue / Heap")
            data_structures.append("Min/Max Heap")
            time_complexity = "O(N log K) — heap operations"
            space_complexity = "O(K) — elements retained in heap"

        if any(kw in code_lower for kw in ["deque", "queue", "bfs"]):
            approaches.append("Breadth-First Search (BFS)")
            data_structures.append("Queue / Deque")
            time_complexity = "O(V + E) — level-order traversal"
            space_complexity = "O(V) — queue size"

        if any(kw in code_lower for kw in ["def dfs", "dfs(", "recursion", "backtrack"]):
            approaches.append("Depth-First Search (DFS) / Backtracking")
            space_complexity = "O(H) — recursion stack depth"

        if any(kw in code_lower for kw in ["dp[", "memo", "dynamic programming"]):
            approaches.append("Dynamic Programming")
            data_structures.append("DP Table / Array")
            time_complexity = "O(N) — optimal subproblem state transitions"
            space_complexity = "O(N) — state array memoization"

        primary_approach = approaches[0] if approaches else "Iterative Simulation"
        if not data_structures:
            data_structures.append("Array / List")

        lang_name = language.capitalize()
        perf_summary = f"⚡ Runtime: {runtime or 'Optimized'} | Memory: {memory or 'Efficient'}"
        diff_tag = f" [{difficulty}]" if difficulty else ""

        steps = [
            f"Parsed and formulated the constraints for '{problem_title}'.",
            f"Utilized a {primary_approach} pattern to eliminate redundant computations.",
            f"Achieved optimal performance: {time_complexity.split('—')[0].strip()} time complexity.",
        ]

        edge_cases = [
            "Empty or single-element inputs",
            "Duplicate values and negative numbers",
            "Maximum constraint boundary values",
        ]

        # Generate a professional LinkedIn caption
        linkedin_caption = (
            f"🚀 Solved: {problem_title}{diff_tag} on LeetCode!\n\n"
            f"💡 Approach: {primary_approach}\n"
            f"⚙️ Language: {lang_name}\n"
            f"⏱️ Complexity: Time: {time_complexity.split('—')[0].strip()} | Space: {space_complexity.split('—')[0].strip()}\n"
            f"{perf_summary}\n\n"
            f"Key Takeaway: Identifying optimal invariants and leveraging appropriate data structures allows us to achieve clean, maintainable, and high-performance solutions.\n\n"
            f"Always enjoying sharpening problem-solving fundamentals! 💻✨\n\n"
            f"#LeetCode #ProblemSolving #Algorithms #DataStructures #{lang_name} #SoftwareEngineering"
        )

        hashtags = [
            "#LeetCode",
            "#Algorithms",
            "#DataStructures",
            f"#{lang_name}",
            "#SoftwareEngineering",
            "#CodingInterview",
        ]

        return GrokAnalysisResult(
            problem_title=problem_title,
            problem_summary=f"Solved {problem_title}{diff_tag} using an optimized {primary_approach} strategy.",
            algorithmic_approach=primary_approach,
            step_by_step_explanation=steps,
            data_structures=data_structures,
            time_complexity=time_complexity,
            space_complexity=space_complexity,
            edge_cases=edge_cases,
            linkedin_caption=linkedin_caption,
            hashtags=hashtags,
        )


grok_service = GrokService()
