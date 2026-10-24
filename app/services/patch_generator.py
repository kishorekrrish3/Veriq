"""Patch Generation and Synthesis Service for VERIQ.
Produces structured code patches via Nebius NVIDIA Nemotron models or curated replay.
"""

import json
import re
from typing import List, Dict, Any, Tuple
from app.core.config import settings
from app.core.logging import logger, redact_sensitive
from app.schemas.runs import PatchFileChange, ModelTier
from app.services.nebius_client import nebius_client

# Curated Replay Scenarios:
# Initial attempt: Modifies calculator.py to add variance & standard_deviation,
# but introduces a regression where factorial(-1) erroneously returns 0 instead of raising ValueError.
REPLAY_ATTEMPT_1_CONTENT = '''"""Sample Calculator Library for VERIQ Verification Engine.
Provides arithmetic, statistical, and validation functions.
"""

import math
from typing import List, Union

Number = Union[int, float]


class Calculator:
    """Scientific and statistical calculation engine."""

    @staticmethod
    def add(a: Number, b: Number) -> Number:
        return a + b

    @staticmethod
    def subtract(a: Number, b: Number) -> Number:
        return a - b

    @staticmethod
    def multiply(a: Number, b: Number) -> Number:
        return a * b

    @staticmethod
    def divide(a: Number, b: Number) -> float:
        if b == 0:
            raise ValueError("Division by zero is undefined")
        return a / b

    @staticmethod
    def power(base: Number, exponent: Number) -> Number:
        if base < 0 and isinstance(exponent, float) and not exponent.is_integer():
            raise ValueError("Negative base cannot be raised to a non-integer power in real domain")
        return math.pow(base, exponent)

    @staticmethod
    def percentage(part: Number, whole: Number) -> float:
        if whole == 0:
            raise ValueError("Whole cannot be zero for percentage calculation")
        return (part / whole) * 100.0

    @staticmethod
    def mean(numbers: List[Number]) -> float:
        if not numbers:
            raise ValueError("Cannot calculate mean of empty list")
        return sum(numbers) / len(numbers)

    @staticmethod
    def median(numbers: List[Number]) -> float:
        if not numbers:
            raise ValueError("Cannot calculate median of empty list")
        sorted_nums = sorted(numbers)
        n = len(sorted_nums)
        mid = n // 2
        if n % 2 == 1:
            return float(sorted_nums[mid])
        else:
            return (sorted_nums[mid - 1] + sorted_nums[mid]) / 2.0

    @staticmethod
    def standard_deviation(numbers: List[Number]) -> float:
        """Calculates population standard deviation."""
        if not numbers:
            raise ValueError("Cannot calculate standard deviation of empty list")
        avg = Calculator.mean(numbers)
        variance = sum((x - avg) ** 2 for x in numbers) / len(numbers)
        return math.sqrt(variance)

    @staticmethod
    def factorial(n: int) -> int:
        if not isinstance(n, int):
            raise TypeError("Factorial requires an integer input")
        # SUBTLE REGRESSION INTRODUCED: returns 0 for negative instead of raising ValueError!
        if n < 0:
            return 0
        return math.factorial(n)
'''

# Repaired attempt: Fixes factorial back to strictly raising ValueError, while keeping standard_deviation
REPLAY_REPAIR_CONTENT = '''"""Sample Calculator Library for VERIQ Verification Engine.
Provides arithmetic, statistical, and validation functions.
"""

import math
from typing import List, Union

Number = Union[int, float]


class Calculator:
    """Scientific and statistical calculation engine."""

    @staticmethod
    def add(a: Number, b: Number) -> Number:
        return a + b

    @staticmethod
    def subtract(a: Number, b: Number) -> Number:
        return a - b

    @staticmethod
    def multiply(a: Number, b: Number) -> Number:
        return a * b

    @staticmethod
    def divide(a: Number, b: Number) -> float:
        if b == 0:
            raise ValueError("Division by zero is undefined")
        return a / b

    @staticmethod
    def power(base: Number, exponent: Number) -> Number:
        if base < 0 and isinstance(exponent, float) and not exponent.is_integer():
            raise ValueError("Negative base cannot be raised to a non-integer power in real domain")
        return math.pow(base, exponent)

    @staticmethod
    def percentage(part: Number, whole: Number) -> float:
        if whole == 0:
            raise ValueError("Whole cannot be zero for percentage calculation")
        return (part / whole) * 100.0

    @staticmethod
    def mean(numbers: List[Number]) -> float:
        if not numbers:
            raise ValueError("Cannot calculate mean of empty list")
        return sum(numbers) / len(numbers)

    @staticmethod
    def median(numbers: List[Number]) -> float:
        if not numbers:
            raise ValueError("Cannot calculate median of empty list")
        sorted_nums = sorted(numbers)
        n = len(sorted_nums)
        mid = n // 2
        if n % 2 == 1:
            return float(sorted_nums[mid])
        else:
            return (sorted_nums[mid - 1] + sorted_nums[mid]) / 2.0

    @staticmethod
    def standard_deviation(numbers: List[Number]) -> float:
        """Calculates population standard deviation."""
        if not numbers:
            raise ValueError("Cannot calculate standard deviation of empty list")
        avg = Calculator.mean(numbers)
        variance = sum((x - avg) ** 2 for x in numbers) / len(numbers)
        return math.sqrt(variance)

    @staticmethod
    def factorial(n: int) -> int:
        if not isinstance(n, int):
            raise TypeError("Factorial requires an integer input")
        if n < 0:
            raise ValueError("Factorial is undefined for negative integers")
        return math.factorial(n)
'''


class PatchGenerator:
    """Generates code patches using Nebius inference or recorded replay."""

    async def generate_patch(
        self,
        task_title: str,
        task_description: str,
        files_context: Dict[str, str],
        model_id: str,
        is_repair: bool = False,
        failure_diagnostics: str = "",
        force_replay: bool = False,
    ) -> Tuple[List[PatchFileChange], Dict[str, int], float]:
        """Synthesizes code modifications.
        Returns: (changes_list, usage_dict, latency_ms)
        """
        if settings.is_live_inference_configured and not force_replay:
            return await self._generate_live_patch(
                task_title=task_title,
                task_description=task_description,
                files_context=files_context,
                model_id=model_id,
                is_repair=is_repair,
                failure_diagnostics=failure_diagnostics,
            )
        else:
            return self._generate_replay_patch(is_repair)

    def _generate_replay_patch(self, is_repair: bool) -> Tuple[List[PatchFileChange], Dict[str, int], float]:
        """Provides realistic recorded replay patches demonstrating failure & repair."""
        if not is_repair:
            content = REPLAY_ATTEMPT_1_CONTENT
            tokens = {"prompt_tokens": 820, "completion_tokens": 460, "total_tokens": 1280}
            latency = 1240.0
        else:
            content = REPLAY_REPAIR_CONTENT
            tokens = {"prompt_tokens": 1150, "completion_tokens": 475, "total_tokens": 1625}
            latency = 1890.0

        changes = [
            PatchFileChange(
                file_path="calculator.py",
                action="modify",
                new_content=content,
            )
        ]
        return changes, tokens, latency

    async def _generate_live_patch(
        self,
        task_title: str,
        task_description: str,
        files_context: Dict[str, str],
        model_id: str,
        is_repair: bool,
        failure_diagnostics: str,
    ) -> Tuple[List[PatchFileChange], Dict[str, int], float]:
        """Calls Nebius Token Factory for real NVIDIA Nemotron model generation."""
        system_prompt = (
            "You are VERIQ's deterministic code generation agent. "
            "You must generate complete, syntactically flawless Python code. "
            "Respond ONLY with a JSON object in the following format:\n"
            "{\n"
            '  "files": [\n'
            '    {\n'
            '      "file_path": "relative/path/to/file.py",\n'
            '      "action": "modify",\n'
            '      "new_content": "COMPLETE FILE CONTENT"\n'
            "    }\n"
            "  ]\n"
            "}\n"
            "Do NOT include markdown backticks around the JSON. Provide only valid JSON."
        )

        user_prompt = f"Task: {task_title}\n\nDescription: {task_description}\n\nExisting Files:\n"
        for path, code in files_context.items():
            user_prompt += f"\n--- {path} ---\n{code}\n"

        if is_repair:
            user_prompt += f"\nCRITICAL: A previous test check FAILED with diagnostics:\n{failure_diagnostics}\nFix this specific regression while preserving all functionality."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        raw_response, usage, latency = await nebius_client.generate_chat_completion(
            model=model_id,
            messages=messages,
            temperature=0.1,
            max_tokens=3000,
        )

        # Parse JSON from response with resilience to preambles, reasoning traces, or markdown fences
        cleaned = raw_response.strip()
        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            cleaned = cleaned[start_idx : end_idx + 1]

        parsed = json.loads(cleaned)
        changes = [
            PatchFileChange(
                file_path=item["file_path"],
                action=item.get("action", "modify"),
                new_content=item["new_content"],
            )
            for item in parsed.get("files", [])
        ]

        return changes, usage, latency


patch_generator = PatchGenerator()
