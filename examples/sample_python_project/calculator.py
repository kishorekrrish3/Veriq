"""Sample Calculator Library for VERIQ Verification Engine.
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
    def factorial(n: int) -> int:
        if not isinstance(n, int):
            raise TypeError("Factorial requires an integer input")
        if n < 0:
            raise ValueError("Factorial is undefined for negative integers")
        return math.factorial(n)
