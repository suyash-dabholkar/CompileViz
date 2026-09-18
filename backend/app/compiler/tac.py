"""
The three-address code (TAC) instruction shape every op in tac_generator.py
produces, and that optimizer.py (Milestone 11) will consume and rewrite.

Every instruction fits the same (op, arg1, arg2, result) quadruple, the
classic TAC representation, just with different fields meaningful for
different ops:

    op          arg1     arg2     result   meaning
    "="         value    -        x        x = value
    "+","-",... left     right    t        t = left op right   (binary)
    "-","!"     operand  -        t        t = op operand      (unary)
    "LABEL"     -        -        L1       L1:
    "GOTO"      -        -        L1       goto L1
    "IF_FALSE"  cond     -        L1       if not cond goto L1
    "PARAM"     value    -        -        param value   (before a CALL)
    "CALL"      name     argc     t        t = call name, argc params
    "RETURN"    value?   -        -        return value  (value optional)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

_BINARY_OPS = {
    "+", "-", "*", "/", "<", ">", "<=", ">=", "==", "!=", "&&", "||",
}
_UNARY_OPS = {"UNARY-", "UNARY!"}


@dataclass
class TACInstr:
    op: str
    arg1: Optional[str] = None
    arg2: Optional[str] = None
    result: Optional[str] = None

    def text(self) -> str:
        """The human-readable line the dashboard shows, e.g. 't1 = a + b'."""
        if self.op == "=":
            return f"{self.result} = {self.arg1}"
        if self.op in _BINARY_OPS:
            return f"{self.result} = {self.arg1} {self.op} {self.arg2}"
        if self.op == "UNARY-":
            return f"{self.result} = -{self.arg1}"
        if self.op == "UNARY!":
            return f"{self.result} = !{self.arg1}"
        if self.op == "LABEL":
            return f"{self.result}:"
        if self.op == "GOTO":
            return f"GOTO {self.result}"
        if self.op == "IF_FALSE":
            return f"IF_FALSE {self.arg1} GOTO {self.result}"
        if self.op == "PARAM":
            return f"PARAM {self.arg1}"
        if self.op == "CALL":
            return f"{self.result} = CALL {self.arg1}, {self.arg2}"
        if self.op == "RETURN":
            return "RETURN" if self.arg1 is None else f"RETURN {self.arg1}"
        raise ValueError(f"Unknown TAC op: {self.op!r}")

    def to_dict(self) -> dict:
        return {
            "op": self.op,
            "arg1": self.arg1,
            "arg2": self.arg2,
            "result": self.result,
            "text": self.text(),
        }
