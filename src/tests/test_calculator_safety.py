from builtin_tools.calculator import _calculate


def test_calculator_basic_expression():
    result = _calculate({"expression": "2 + 3 * 4"})
    assert result.success is True
    assert result.output["result"] == 14


def test_calculator_allows_math_functions_and_constants():
    result = _calculate({"expression": "sin(pi/2)"})
    assert result.success is True
    assert abs(result.output["result"] - 1.0) < 1e-9


def test_calculator_rejects_non_math_code():
    result = _calculate({"expression": "__import__('os').system('echo hacked')"})
    assert result.success is False
    assert "Math error" in result.error
