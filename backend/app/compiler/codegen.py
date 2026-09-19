"""
Code generation: lowers TAC (Milestone 10, after optimization in
Milestone 11) into instructions for a simple stack machine, the last
phase of the PRD's six-phase pipeline.

The stack machine has no registers, every operation pops its operands
off the top of the stack and pushes its result back:

    PUSH_CONST v    push a literal
    LOAD x          push the value of variable x
    STORE x         pop the top and store it into variable x
    ADD/SUB/MUL/DIV pop two, push the result
    LT/GT/LE/GE/EQ/NE  pop two, push a bool
    AND/OR          pop two, push a bool
    NEG/NOT         pop one, push the result
    LABEL L         a jump target, no-op at runtime
    JMP L           unconditional jump to L
    JMP_FALSE L     pop the top, jump to L if it was false
    CALL name, argc pop argc values (pushed by preceding PARAM-derived
                    pushes), perform the call, push its result (a
                    dummy value for a void built-in like print, so the
                    stack discipline never breaks even though the
                    value is never meaningfully used)
    RET             stop execution; if a value was pushed just before
                    this, that's the returned value

Every TAC operand is either a literal (an int/float/bool lexeme, or a
double-quoted string) or a name (a variable or a %-prefixed temp).
_push_operand tells the two apart and emits PUSH_CONST or LOAD
accordingly, this module doesn't otherwise care which one it is.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.compiler.tac import TACInstr

_BINARY_OP_NAMES = {
    "+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV",
    "<": "LT", ">": "GT", "<=": "LE", ">=": "GE",
    "==": "EQ", "!=": "NE", "&&": "AND", "||": "OR",
}
_NO_OPERAND_OPS = set(_BINARY_OP_NAMES.values()) | {"NEG", "NOT", "RET"}


def _is_literal(operand: str) -> bool:
    if operand.startswith('"') and operand.endswith('"'):
        return True
    if operand in ("true", "false"):
        return True
    try:
        float(operand)  # covers both int and float lexemes
        return True
    except ValueError:
        return False


@dataclass
class Instr:
    op: str
    arg: Optional[str] = None
    arg2: Optional[str] = None

    def text(self) -> str:
        if self.op in _NO_OPERAND_OPS:
            return self.op
        if self.op == "LABEL":
            return f"{self.arg}:"
        if self.op == "CALL":
            return f"CALL {self.arg}, {self.arg2}"
        return f"{self.op} {self.arg}"

    def to_dict(self) -> dict:
        return {"op": self.op, "arg": self.arg, "arg2": self.arg2, "text": self.text()}


class CodeGenerator:
    def __init__(self) -> None:
        self.instructions: list[Instr] = []

    def _emit(self, op: str, arg: str | None = None, arg2: str | None = None) -> None:
        self.instructions.append(Instr(op, arg, arg2))

    def _push_operand(self, operand: str) -> None:
        self._emit("PUSH_CONST" if _is_literal(operand) else "LOAD", operand)

    def generate(self, tac: list[TACInstr]) -> list[Instr]:
        for instr in tac:
            self._gen_one(instr)
        return self.instructions

    def _gen_one(self, instr: TACInstr) -> None:
        op = instr.op

        if op == "=":
            self._push_operand(instr.arg1)
            self._emit("STORE", instr.result)

        elif op in _BINARY_OP_NAMES:
            self._push_operand(instr.arg1)
            self._push_operand(instr.arg2)
            self._emit(_BINARY_OP_NAMES[op])
            self._emit("STORE", instr.result)

        elif op == "UNARY-":
            self._push_operand(instr.arg1)
            self._emit("NEG")
            self._emit("STORE", instr.result)

        elif op == "UNARY!":
            self._push_operand(instr.arg1)
            self._emit("NOT")
            self._emit("STORE", instr.result)

        elif op == "LABEL":
            self._emit("LABEL", instr.result)

        elif op == "GOTO":
            self._emit("JMP", instr.result)

        elif op == "IF_FALSE":
            self._push_operand(instr.arg1)
            self._emit("JMP_FALSE", instr.result)

        elif op == "PARAM":
            self._push_operand(instr.arg1)

        elif op == "CALL":
            self._emit("CALL", instr.arg1, instr.arg2)
            self._emit("STORE", instr.result)

        elif op == "RETURN":
            if instr.arg1 is not None:
                self._push_operand(instr.arg1)
            self._emit("RET")

        else:
            raise ValueError(f"Unknown TAC op: {op!r}")


def generate_code(tac: list[TACInstr]) -> list[Instr]:
    return CodeGenerator().generate(tac)
