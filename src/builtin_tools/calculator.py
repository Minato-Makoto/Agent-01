"""Built-in tool: Calculator (Math skill)."""

import ast
import math
import logging
from agentforge.tools import Tool, ToolRegistry, ToolResult

logger = logging.getLogger(__name__)


SAFE_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
}

SAFE_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "ceil": math.ceil,
    "floor": math.floor,
    "pow": pow,
}

SAFE_BIN_OPS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.Mod: lambda a, b: a % b,
    ast.Pow: lambda a, b: a ** b,
}

SAFE_UNARY_OPS = {
    ast.UAdd: lambda a: +a,
    ast.USub: lambda a: -a,
}


def _evaluate_ast(node):
    if isinstance(node, ast.Expression):
        return _evaluate_ast(node.body)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Only numeric constants are allowed")

    if isinstance(node, ast.Name):
        if node.id in SAFE_CONSTANTS:
            return SAFE_CONSTANTS[node.id]
        raise ValueError(f"Unknown identifier: {node.id}")

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in SAFE_BIN_OPS:
            raise ValueError(f"Operator not allowed: {op_type.__name__}")
        left = _evaluate_ast(node.left)
        right = _evaluate_ast(node.right)
        return SAFE_BIN_OPS[op_type](left, right)

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in SAFE_UNARY_OPS:
            raise ValueError(f"Unary operator not allowed: {op_type.__name__}")
        operand = _evaluate_ast(node.operand)
        return SAFE_UNARY_OPS[op_type](operand)

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only direct function calls are allowed")
        fn_name = node.func.id
        fn = SAFE_FUNCTIONS.get(fn_name)
        if fn is None:
            raise ValueError(f"Function not allowed: {fn_name}")
        if node.keywords:
            raise ValueError("Keyword arguments are not allowed")
        args = [_evaluate_ast(arg) for arg in node.args]
        return fn(*args)

    raise ValueError(f"Expression not allowed: {type(node).__name__}")


def _safe_eval(expression: str):
    tree = ast.parse(expression, mode="eval")
    return _evaluate_ast(tree)


def _calculate(args: dict) -> ToolResult:
    """Evaluate a mathematical expression safely."""
    expression = args.get("expression", "")
    if not expression:
        return ToolResult(
            success=False,
            output=None,
            error=(
                "Missing 'expression'. Provide a math expression like "
                "'2 + 3 * 4' or 'sqrt(144)'."
            ),
        )

    try:
        result = _safe_eval(expression)
        return ToolResult(success=True, output={"result": result, "expression": expression})
    except Exception as e:
        return ToolResult.from_exception(e, context="Math error", logger=logger)


def register(registry: ToolRegistry, skill_name: str = "Math") -> None:
    """Register the calculate tool."""
    tools = [
        Tool(
            name="calculate",
            description="Evaluate a mathematical expression. Supports: +, -, *, /, **, sqrt, sin, cos, tan, log, log10, ceil, floor, abs, pi, e.",
            input_schema={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "A math expression (e.g. '2 + 3 * 4', 'sqrt(144)', 'sin(pi/2)')."
                    },
                },
                "required": ["expression"],
            },
            execute_fn=_calculate,
        ),
    ]
    registry.register_skill(skill_name, tools)
