"""
A small interpreter for the stack-machine instructions codegen.py
produces, letting the dashboard actually run a program and show its
output, not just the generated code. Optional per the PRD, but genuinely
useful: it's the difference between "here's the assembly" and "here's
what your program does."

Safety: this runs on the server, so a buggy or malicious program with
an infinite loop can't be allowed to hang the process. Execution is
capped at MAX_STEPS; going over that is reported as a normal result
(program_error set), not a server error.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.compiler.codegen import Instr

MAX_STEPS = 200_000


def _parse_literal(text: str):
    if text.startswith('"') and text.endswith('"'):
        return text[1:-1]
    if text == "true":
        return True
    if text == "false":
        return False
    try:
        return int(text)
    except ValueError:
        pass
    return float(text)


def _binary(op: str, a, b):
    if op == "ADD":
        return a + b
    if op == "SUB":
        return a - b
    if op == "MUL":
        return a * b
    if op == "DIV":
        if b == 0:
            raise ZeroDivisionError()
        return a / b if isinstance(a, float) or isinstance(b, float) else a // b
    if op == "LT":
        return a < b
    if op == "GT":
        return a > b
    if op == "LE":
        return a <= b
    if op == "GE":
        return a >= b
    if op == "EQ":
        return a == b
    if op == "NE":
        return a != b
    if op == "AND":
        return bool(a) and bool(b)
    if op == "OR":
        return bool(a) or bool(b)
    raise ValueError(f"Unknown binary op: {op!r}")


def _format_value(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


@dataclass
class InterpreterResult:
    output: list[str] = field(default_factory=list)
    variables: dict[str, object] = field(default_factory=dict)
    steps: int = 0
    runtime_error: str | None = None

    def to_dict(self) -> dict:
        return {
            "output": self.output,
            "variables": {k: _format_value(v) for k, v in self.variables.items() if not k.startswith("%")},
            "steps": self.steps,
            "runtime_error": self.runtime_error,
        }


def run_program(instructions: list[Instr]) -> InterpreterResult:
    labels = {instr.arg: i for i, instr in enumerate(instructions) if instr.op == "LABEL"}

    stack: list = []
    variables: dict[str, object] = {}
    output: list[str] = []
    pc = 0
    steps = 0

    while pc < len(instructions):
        steps += 1
        if steps > MAX_STEPS:
            return InterpreterResult(
                output, variables, steps,
                runtime_error=f"Execution stopped after {MAX_STEPS} steps (likely an infinite loop).",
            )

        instr = instructions[pc]
        op = instr.op

        try:
            if op == "PUSH_CONST":
                stack.append(_parse_literal(instr.arg))
                pc += 1
            elif op == "LOAD":
                if instr.arg not in variables:
                    return InterpreterResult(
                        output, variables, steps,
                        runtime_error=f"Variable '{instr.arg}' read before being assigned.",
                    )
                stack.append(variables[instr.arg])
                pc += 1
            elif op == "STORE":
                variables[instr.arg] = stack.pop()
                pc += 1
            elif op in ("ADD", "SUB", "MUL", "DIV", "LT", "GT", "LE", "GE", "EQ", "NE", "AND", "OR"):
                b = stack.pop()
                a = stack.pop()
                stack.append(_binary(op, a, b))
                pc += 1
            elif op == "NEG":
                stack.append(-stack.pop())
                pc += 1
            elif op == "NOT":
                stack.append(not stack.pop())
                pc += 1
            elif op == "LABEL":
                pc += 1
            elif op == "JMP":
                pc = labels[instr.arg]
            elif op == "JMP_FALSE":
                condition = stack.pop()
                pc = labels[instr.arg] if not condition else pc + 1
            elif op == "CALL":
                name, argc = instr.arg, int(instr.arg2)
                args = [stack.pop() for _ in range(argc)][::-1]
                if name == "print":
                    output.append(" ".join(_format_value(a) for a in args))
                    stack.append(0)  # dummy return value, print is void
                else:
                    return InterpreterResult(
                        output, variables, steps,
                        runtime_error=f"Call to unknown function '{name}'.",
                    )
                pc += 1
            elif op == "RET":
                break
            else:
                return InterpreterResult(
                    output, variables, steps, runtime_error=f"Unknown instruction: {op}"
                )
        except IndexError:
            return InterpreterResult(
                output, variables, steps,
                runtime_error=f"Stack underflow at instruction {steps}: {instr.text()}",
            )
        except ZeroDivisionError:
            return InterpreterResult(
                output, variables, steps, runtime_error="Division by zero."
            )

    return InterpreterResult(output, variables, steps)
