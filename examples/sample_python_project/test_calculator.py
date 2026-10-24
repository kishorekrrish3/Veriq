"""Unit and regression tests for Calculator.
"""

import pytest
from calculator import Calculator


def test_basic_arithmetic():
    assert Calculator.add(2, 3) == 5
    assert Calculator.subtract(10, 4) == 6
    assert Calculator.multiply(3, 7) == 21
    assert Calculator.divide(15, 3) == 5.0


def test_division_by_zero():
    with pytest.raises(ValueError, match="Division by zero"):
        Calculator.divide(10, 0)


def test_power():
    assert Calculator.power(2, 3) == 8.0
    assert Calculator.power(9, 0.5) == 3.0
    with pytest.raises(ValueError):
        Calculator.power(-4, 0.5)


def test_percentage():
    assert Calculator.percentage(25, 100) == 25.0
    with pytest.raises(ValueError):
        Calculator.percentage(10, 0)


def test_mean():
    assert Calculator.mean([1, 2, 3, 4, 5]) == 3.0
    with pytest.raises(ValueError):
        Calculator.mean([])


def test_median():
    assert Calculator.median([1, 3, 2]) == 2.0
    assert Calculator.median([1, 2, 3, 4]) == 2.5
    with pytest.raises(ValueError):
        Calculator.median([])


def test_factorial():
    assert Calculator.factorial(0) == 1
    assert Calculator.factorial(5) == 120
    with pytest.raises(ValueError):
        Calculator.factorial(-1)
    with pytest.raises(TypeError):
        Calculator.factorial(3.5)  # type: ignore
