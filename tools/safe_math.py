"""Safe arithmetic evaluation — no eval(), no code execution.

Parses the expression into an AST and walks it, allowing only a fixed
whitelist of numeric operations and math functions. Anything else
(attribute access, names, calls to unknown functions, comprehensions)
raises ValueError. This replaces the previous eval()-based calculator,
which executed arbitrary user input.
"""

from __future__ import annotations

import ast
import math
import operator

# Allowed binary / unary operators
_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

# Allowed names (constants)
_NAMES = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
    "inf": math.inf,
}

# Allowed function calls
_FUNCS = {
    "sqrt": math.sqrt,
    "log": math.log,        # log(x) or log(x, base)
    "log10": math.log10,
    "log2": math.log2,
    "ln": math.log,
    "exp": math.exp,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "sinh": math.sinh,
    "cosh": math.cosh,
    "tanh": math.tanh,
    "radians": math.radians,
    "degrees": math.degrees,
    "factorial": math.factorial,
    "gcd": math.gcd,
    "comb": math.comb,
    "perm": math.perm,
    "abs": abs,
    "round": round,
    "floor": math.floor,
    "ceil": math.ceil,
    "min": min,
    "max": max,
    "pow": pow,
}

# Hard cap to stop pathological inputs (e.g. factorial(99999))
_MAX_POW_EXP = 1000
_MAX_FACTORIAL = 1000


def _eval(node: ast.AST) -> float | int:
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant: {node.value!r}")
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _BIN_OPS:
            raise ValueError(f"Operator not allowed: {op_type.__name__}")
        left, right = _eval(node.left), _eval(node.right)
        if op_type is ast.Pow and isinstance(right, (int, float)) and right > _MAX_POW_EXP:
            raise ValueError("Exponent too large")
        return _BIN_OPS[op_type](left, right)
    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _UNARY_OPS:
            raise ValueError(f"Unary operator not allowed: {op_type.__name__}")
        return _UNARY_OPS[op_type](_eval(node.operand))
    if isinstance(node, ast.Name):
        if node.id in _NAMES:
            return _NAMES[node.id]
        raise ValueError(f"Unknown name: {node.id}")
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only direct function calls are allowed")
        fname = node.func.id
        if fname not in _FUNCS:
            raise ValueError(f"Function not allowed: {fname}")
        if node.keywords:
            raise ValueError("Keyword arguments are not allowed")
        args = [_eval(a) for a in node.args]
        if fname == "factorial" and args and args[0] > _MAX_FACTORIAL:
            raise ValueError("Factorial argument too large")
        return _FUNCS[fname](*args)
    raise ValueError(f"Unsupported expression element: {type(node).__name__}")


def safe_eval(expression: str) -> float | int:
    """Evaluate a math expression safely. Raises ValueError on anything unsafe."""
    tree = ast.parse(expression, mode="eval")
    return _eval(tree)
