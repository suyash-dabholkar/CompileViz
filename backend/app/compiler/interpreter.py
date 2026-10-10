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


def _describe(op: str, instr: Instr, before: list, after: list, jumped_to) -> str:
    """One plain sentence about what this instruction just did to the
    machine. The stack is the whole lesson here, so every description
    says what went on or came off it.
    """
    if op == "PUSH_CONST":
        return (
            f"PUSH_CONST puts the literal {instr.arg} on top of the stack. "
            f"Operands always arrive this way before anything consumes them."
        )
    if op == "LOAD":
        return (
            f"LOAD reads the variable '{instr.arg}' and pushes its current "
            f"value, {_format_value(after[-1])}, onto the stack."
        )
    if op == "STORE":
        return (
            f"STORE pops {_format_value(before[-1])} off the stack and writes "
            f"it into '{instr.arg}'. The stack shrinks by one."
        )
    if op in ("ADD", "SUB", "MUL", "DIV", "LT", "GT", "LE", "GE", "EQ", "NE", "AND", "OR"):
        return (
            f"{op} pops the top two values, {_format_value(before[-2])} and "
            f"{_format_value(before[-1])}, and pushes the single result "
            f"{_format_value(after[-1])}. Two off, one on: that is why a stack "
            f"machine needs no registers."
        )
    if op in ("NEG", "NOT"):
        return (
            f"{op} replaces the top of the stack, {_format_value(before[-1])}, "
            f"with {_format_value(after[-1])}."
        )
    if op == "LABEL":
        return (
            f"'{instr.arg}' is a label: a jump target, not an instruction. It "
            f"does nothing at runtime and execution falls straight through."
        )
    if op == "JMP":
        return (
            f"JMP moves execution unconditionally to '{instr.arg}', which is "
            f"instruction {jumped_to}. Nothing on the stack changes."
        )
    if op == "JMP_FALSE":
        taken = jumped_to is not None
        return (
            f"JMP_FALSE pops the condition, which was "
            f"{_format_value(before[-1])}. It is "
            + (
                f"false, so execution jumps to '{instr.arg}' (instruction "
                f"{jumped_to}) and the branch body is skipped."
                if taken
                else "true, so no jump happens and execution carries straight on "
                "into the branch body."
            )
        )
    if op == "CALL":
        return (
            f"CALL runs '{instr.arg}' with {instr.arg2} argument(s) taken off "
            f"the stack, then pushes its return value."
        )
    if op == "RET":
        return "RET ends the program."
    return f"{op} executes."


def run_program(instructions: list[Instr], *, tracer=None) -> InterpreterResult:
    """Execute the stack-machine program.

    Pass a `tracer` (app.trace.Tracer) to record the machine state after
    every instruction. All of it - the stack, the variables, the program
    counter - already existed as locals here; without a tracer the only
    thing that escaped was a step *count*.
    """
    labels = {instr.arg: i for i, instr in enumerate(instructions) if instr.op == "LABEL"}

    stack: list = []
    variables: dict[str, object] = {}
    output: list[str] = []
    pc = 0
    steps = 0

    if tracer:
        tracer.phase("run")

    while pc < len(instructions):
        steps += 1
        if steps > MAX_STEPS:
            return InterpreterResult(
                output, variables, steps,
                runtime_error=f"Execution stopped after {MAX_STEPS} steps (likely an infinite loop).",
            )

        instr = instructions[pc]
        op = instr.op
        before_stack = list(stack) if tracer else None
        before_pc = pc
        output_before = len(output)

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

        if tracer:
            jumped_to = pc if pc != before_pc + 1 else None
            printed = output[output_before:]
            conditional = op == "JMP_FALSE"
            tracer.step(
                "vm.jump" if conditional else "vm.step",
                title=f"{before_pc}: {instr.text()}",
                explain=_describe(op, instr, before_stack, stack, jumped_to),
                # A conditional branch is the one place the interesting
                # answer is not the stack but whether control moved, so
                # that is what it reports and asks about.
                result=(jumped_to is not None) if conditional else [
                    _format_value(v) for v in stack
                ],
                pc=before_pc,
                next_pc=pc,
                op=op,
                text=instr.text(),
                stack_before=[_format_value(v) for v in before_stack],
                stack=[_format_value(v) for v in stack],
                variables={
                    name: _format_value(value)
                    for name, value in variables.items()
                    if not name.startswith("%")
                },
                printed=printed,
                highlight={"rows": [before_pc]},
                ask="Does this branch jump?" if conditional else None,
            )

    if tracer:
        tracer.step(
            "vm.halt",
            title=f"Halted after {steps} instructions",
            explain=(
                f"Execution ran off the end of the program after {steps} "
                f"instructions. The stack is "
                + ("empty, as it should be once every operand has been "
                   "consumed." if not stack else
                   f"{[_format_value(v) for v in stack]}, which is left over.")
            ),
            result=steps,
            stack=[_format_value(v) for v in stack],
            variables={
                name: _format_value(value)
                for name, value in variables.items()
                if not name.startswith("%")
            },
            output=list(output),
        )

    return InterpreterResult(output, variables, steps)
