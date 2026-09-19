"""
Three classical optimizations over the TAC from Milestone 10, run in
the order that actually compounds them: folding first (since it can
turn a computed value into a literal), then common subexpression
elimination (folding can expose new duplicate expressions), then dead
code elimination last (both earlier passes can leave a temp assigned
but never read).

Every pass is careful about control flow: a LABEL is treated as a
basic-block boundary and clears whatever the pass was tracking
(known constants, or available expressions). That's a conservative
choice, not a precise one, a full compiler would do real data-flow
analysis across the control-flow graph, but it's always SAFE: nothing
gets propagated or reused across a point where a different execution
path could have changed it. Getting less optimization than a
research-grade compiler in exchange for evident correctness is the
right trade for this project.

Temps (t1, t2, ...) are effectively single-assignment: tac_generator.py
never reuses a temp name once it's created one. That's what makes the
dead code elimination pass simple and safe: if a temp is never read
again after its one definition, it's globally dead, no liveness
analysis across branches required.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.compiler.tac import TACInstr

_BINARY_ARITH = {"+", "-", "*", "/"}
_BINARY_RELATIONAL = {"<", ">", "<=", ">=", "==", "!="}
_BINARY_LOGICAL = {"&&", "||"}
_PURE_BINARY_OPS = _BINARY_ARITH | _BINARY_RELATIONAL | _BINARY_LOGICAL
_PURE_UNARY_OPS = {"UNARY-", "UNARY!"}
_PURE_OPS = _PURE_BINARY_OPS | _PURE_UNARY_OPS | {"="}


def _is_temp(name: str | None) -> bool:
    return name is not None and name.startswith("%t") and name[2:].isdigit()


def _parse_constant(value: str) -> tuple[bool, object]:
    """Returns (is_constant, python_value). Recognizes int, float, and
    bool literals, the only kinds this language's operators need.
    """
    if value in ("true", "false"):
        return True, value == "true"
    try:
        return True, int(value)
    except ValueError:
        pass
    try:
        return True, float(value)
    except ValueError:
        pass
    return False, None


def _format_constant(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _fold_binary(op: str, left, right) -> object | None:
    try:
        if op == "+":
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            return left / right if isinstance(left, float) or isinstance(right, float) else left // right
        if op == "<":
            return left < right
        if op == ">":
            return left > right
        if op == "<=":
            return left <= right
        if op == ">=":
            return left >= right
        if op == "==":
            return left == right
        if op == "!=":
            return left != right
        if op == "&&":
            return bool(left) and bool(right)
        if op == "||":
            return bool(left) or bool(right)
    except ZeroDivisionError:
        return None
    return None


@dataclass
class OptimizationResult:
    original: list[TACInstr]
    after_constant_folding: list[TACInstr]
    after_cse: list[TACInstr]
    after_dce: list[TACInstr]

    @property
    def optimized(self) -> list[TACInstr]:
        return self.after_dce

    def to_dict(self) -> dict:
        return {
            "original": [i.to_dict() for i in self.original],
            "after_constant_folding": [i.to_dict() for i in self.after_constant_folding],
            "after_cse": [i.to_dict() for i in self.after_cse],
            "after_dce": [i.to_dict() for i in self.after_dce],
            "instructions_removed": len(self.original) - len(self.after_dce),
        }


def constant_fold(instructions: list[TACInstr]) -> list[TACInstr]:
    """Folds constant expressions and propagates known constant values
    forward within a basic block, e.g. `t1 = 3 * 4` becomes `t1 = 12`,
    and a later `t2 = t1 + 1` becomes `t2 = 13` in the same pass, since
    t1's value is now known.
    """
    result: list[TACInstr] = []
    known: dict[str, str] = {}

    for instr in instructions:
        if instr.op == "LABEL":
            known = {}
            result.append(instr)
            continue

        arg1 = known.get(instr.arg1, instr.arg1) if instr.arg1 is not None else None
        arg2 = known.get(instr.arg2, instr.arg2) if instr.op in _PURE_BINARY_OPS and instr.arg2 is not None else instr.arg2

        new_instr = TACInstr(instr.op, arg1, arg2, instr.result)

        if instr.op == "=" :
            is_const, value = _parse_constant(arg1)
            if is_const:
                known[instr.result] = arg1
            else:
                known.pop(instr.result, None)
            result.append(new_instr)
            continue

        if instr.op in _PURE_BINARY_OPS:
            left_const, left_val = _parse_constant(arg1)
            right_const, right_val = _parse_constant(arg2)
            if left_const and right_const:
                folded = _fold_binary(instr.op, left_val, right_val)
                if folded is not None:
                    folded_str = _format_constant(folded)
                    result.append(TACInstr("=", folded_str, result=instr.result))
                    known[instr.result] = folded_str
                    continue
            known.pop(instr.result, None)
            result.append(new_instr)
            continue

        if instr.op in _PURE_UNARY_OPS:
            operand_const, operand_val = _parse_constant(arg1)
            if operand_const:
                folded = -operand_val if instr.op == "UNARY-" else (not operand_val)
                folded_str = _format_constant(folded)
                result.append(TACInstr("=", folded_str, result=instr.result))
                known[instr.result] = folded_str
                continue
            known.pop(instr.result, None)
            result.append(new_instr)
            continue

        # Anything else (LABEL handled above, GOTO/IF_FALSE/PARAM/CALL/
        # RETURN): still substitute known constants into its operands
        # (e.g. IF_FALSE on a now-constant condition), but the
        # instruction itself is never folded away, and if it assigns a
        # result (CALL does), that result is no longer a known constant.
        if instr.op == "CALL":
            known.pop(instr.result, None)
        result.append(new_instr)

    return result


def eliminate_common_subexpressions(instructions: list[TACInstr]) -> list[TACInstr]:
    """Within a basic block, reuses an already-computed value instead
    of recomputing the exact same expression, as long as neither
    operand has been reassigned since.
    """
    result: list[TACInstr] = []
    available: dict[tuple, str] = {}
    substitute: dict[str, str] = {}

    def resolve(name: str | None) -> str | None:
        return substitute.get(name, name) if name is not None else None

    def invalidate(changed_name: str) -> None:
        for key in [k for k in available if changed_name in (k[1], k[2])]:
            del available[key]

    for instr in instructions:
        if instr.op == "LABEL":
            available = {}
            substitute = {}
            result.append(instr)
            continue

        arg1 = resolve(instr.arg1)
        arg2 = resolve(instr.arg2) if instr.op in _PURE_BINARY_OPS else instr.arg2

        if instr.op in _PURE_BINARY_OPS or instr.op in _PURE_UNARY_OPS:
            key = (instr.op, arg1, arg2)
            if key in available:
                substitute[instr.result] = available[key]
                # Dropped entirely: every later reference to instr.result
                # is redirected to the earlier, equivalent temp instead.
                continue
            available[key] = instr.result
            result.append(TACInstr(instr.op, arg1, arg2, instr.result))
            continue

        if instr.op == "=":
            new_instr = TACInstr("=", arg1, result=instr.result)
            if not _is_temp(instr.result):
                invalidate(instr.result)
            result.append(new_instr)
            continue

        new_instr = TACInstr(instr.op, arg1, instr.arg2, instr.result)
        if instr.result is not None and not _is_temp(instr.result):
            invalidate(instr.result)
        result.append(new_instr)

    return result


def eliminate_dead_code(instructions: list[TACInstr]) -> list[TACInstr]:
    """Drops a temp's defining instruction if that temp is never read
    anywhere later. Safe without full liveness analysis because temps
    are single-assignment (see module docstring); never removes an
    instruction with a side effect (CALL, PARAM, GOTO, IF_FALSE,
    LABEL, RETURN) or one that assigns a real variable, only ever a
    temp whose value truly goes unused.
    """
    used: set[str] = set()
    for instr in instructions:
        for operand in (instr.arg1, instr.arg2):
            if operand is not None:
                used.add(operand)

    keep: list[TACInstr] = []
    for instr in instructions:
        defines_dead_temp = (
            instr.op in _PURE_OPS
            and _is_temp(instr.result)
            and instr.result not in used
        )
        if defines_dead_temp:
            continue
        keep.append(instr)
    return keep


def optimize(instructions: list[TACInstr]) -> OptimizationResult:
    after_folding = constant_fold(instructions)
    after_cse = eliminate_common_subexpressions(after_folding)
    after_dce = eliminate_dead_code(after_cse)
    return OptimizationResult(
        original=instructions,
        after_constant_folding=after_folding,
        after_cse=after_cse,
        after_dce=after_dce,
    )
