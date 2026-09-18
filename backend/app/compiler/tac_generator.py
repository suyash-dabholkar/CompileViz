"""
Three-address code generation: walks the AST (Milestone 8) and emits a
flat list of TACInstr (tac.py), the same shape the optimizer
(Milestone 11) and code generator (Milestone 12) build on.

Control flow (if/while) lowers to labels and jumps, the standard
technique:

    if (cond) { A } else { B }        while (cond) { A }
    --------------------------        ------------------
        <cond>                        L_start:
        IF_FALSE cond GOTO L_else         <cond>
        <A>                               IF_FALSE cond GOTO L_end
        GOTO L_end                        <A>
    L_else:                               GOTO L_start
        <B>                           L_end:
    L_end:

Every temporary and label is freshly numbered per TACGenerator instance
(t1, t2, ... and L1, L2, ...), so generating TAC for a whole program
gives every temp and label a unique name throughout.
"""

from __future__ import annotations

from app.compiler.ast_nodes import (
    Assignment,
    BinaryOp,
    Block,
    Call,
    ExprStmt,
    Identifier,
    IfStmt,
    Literal,
    Program,
    ReturnStmt,
    UnaryOp,
    VarDecl,
    WhileStmt,
)
from app.compiler.tac import TACInstr

_UNARY_OP_NAMES = {"-": "UNARY-", "!": "UNARY!"}


class TACGenerator:
    def __init__(self) -> None:
        self.instructions: list[TACInstr] = []
        self._temp_count = 0
        self._label_count = 0

    def new_temp(self) -> str:
        self._temp_count += 1
        return f"t{self._temp_count}"

    def new_label(self) -> str:
        self._label_count += 1
        return f"L{self._label_count}"

    def _emit(self, op: str, arg1=None, arg2=None, result=None) -> None:
        self.instructions.append(TACInstr(op, arg1, arg2, result))

    # -- entry point ------------------------------------------------------

    def generate(self, program: Program) -> list[TACInstr]:
        for stmt in program.statements:
            self._gen_statement(stmt)
        return self.instructions

    # -- statements ---------------------------------------------------------

    def _gen_statement(self, stmt) -> None:
        if isinstance(stmt, VarDecl):
            if stmt.init is not None:
                value = self._gen_expr(stmt.init)
                self._emit("=", value, result=stmt.name)
        elif isinstance(stmt, Assignment):
            value = self._gen_expr(stmt.value)
            self._emit("=", value, result=stmt.name)
        elif isinstance(stmt, IfStmt):
            self._gen_if(stmt)
        elif isinstance(stmt, WhileStmt):
            self._gen_while(stmt)
        elif isinstance(stmt, ReturnStmt):
            value = self._gen_expr(stmt.value) if stmt.value is not None else None
            self._emit("RETURN", value)
        elif isinstance(stmt, Block):
            for inner in stmt.statements:
                self._gen_statement(inner)
        elif isinstance(stmt, ExprStmt):
            self._gen_expr(stmt.expr)  # value discarded, side effects (e.g. a call) kept
        else:
            raise TypeError(f"Unknown statement node: {type(stmt)!r}")

    def _gen_if(self, stmt: IfStmt) -> None:
        cond = self._gen_expr(stmt.condition)
        if stmt.else_block is None:
            end_label = self.new_label()
            self._emit("IF_FALSE", cond, result=end_label)
            self._gen_statement(stmt.then_block)
            self._emit("LABEL", result=end_label)
        else:
            else_label = self.new_label()
            end_label = self.new_label()
            self._emit("IF_FALSE", cond, result=else_label)
            self._gen_statement(stmt.then_block)
            self._emit("GOTO", result=end_label)
            self._emit("LABEL", result=else_label)
            self._gen_statement(stmt.else_block)
            self._emit("LABEL", result=end_label)

    def _gen_while(self, stmt: WhileStmt) -> None:
        start_label = self.new_label()
        end_label = self.new_label()
        self._emit("LABEL", result=start_label)
        cond = self._gen_expr(stmt.condition)
        self._emit("IF_FALSE", cond, result=end_label)
        self._gen_statement(stmt.body)
        self._emit("GOTO", result=start_label)
        self._emit("LABEL", result=end_label)

    # -- expressions --------------------------------------------------------
    # Every _gen_expr call returns an "address": a temp name, a variable
    # name, or a literal's raw lexeme, whatever can stand in as an
    # operand somewhere else.

    def _gen_expr(self, expr) -> str:
        if isinstance(expr, Literal):
            return expr.value

        if isinstance(expr, Identifier):
            return expr.name

        if isinstance(expr, UnaryOp):
            operand = self._gen_expr(expr.operand)
            temp = self.new_temp()
            self._emit(_UNARY_OP_NAMES[expr.op], operand, result=temp)
            return temp

        if isinstance(expr, BinaryOp):
            left = self._gen_expr(expr.left)
            right = self._gen_expr(expr.right)
            temp = self.new_temp()
            self._emit(expr.op, left, right, result=temp)
            return temp

        if isinstance(expr, Call):
            arg_addrs = [self._gen_expr(arg) for arg in expr.args]
            for addr in arg_addrs:
                self._emit("PARAM", addr)
            temp = self.new_temp()
            self._emit("CALL", expr.callee, str(len(arg_addrs)), result=temp)
            return temp

        raise TypeError(f"Unknown expression node: {type(expr)!r}")


def generate_tac(program: Program) -> list[TACInstr]:
    return TACGenerator().generate(program)
