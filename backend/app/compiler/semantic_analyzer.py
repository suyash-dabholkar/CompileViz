"""
Semantic analysis: walks the AST (Milestone 8) once, populating a
scoped symbol table and type-checking every expression and statement.

Catches exactly the error categories the project's PRD calls for:
    - undeclared variable use
    - redeclaration in the same scope
    - type mismatch (var-decl initializer, assignment, conditions,
      operator operands)
    - invalid function-call arity

A note on functions: the parser (Milestone 8) supports function CALLS
in expressions, but the grammar never added a way to DEFINE a
function, there's no `def name(params) { ... }` statement. Rather than
silently pretending arity checking works against user-defined
functions that can't actually exist yet, this module checks calls
against a small table of BUILTIN_FUNCTIONS instead, so the "invalid
call arity" error category is still real and testable. Adding real
function declarations back into the parser's grammar would be a
reasonable follow-up, not something this module works around silently.

Error cascade avoidance: once an expression has already produced an
error (an undeclared variable, a bad call), its inferred type becomes
TYPE_ERROR, which every check below treats as automatically compatible
with anything. That's deliberate, it stops one root-cause mistake from
also triggering a wall of unrelated-looking follow-on errors.
"""

from __future__ import annotations

from dataclasses import dataclass

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
from app.compiler.symbol_table import Symbol, SymbolTable

TYPE_ERROR = "<error>"

_LITERAL_TYPE_MAP = {"INT": "int", "FLOAT": "float", "STRING": "string", "BOOL": "bool"}

_ARITHMETIC_OPS = {"+", "-", "*", "/"}
_RELATIONAL_OPS = {"<", ">", "<=", ">="}
_EQUALITY_OPS = {"==", "!="}
_LOGICAL_OPS = {"&&", "||"}


@dataclass
class FunctionSignature:
    name: str
    param_count: int
    return_type: str


BUILTIN_FUNCTIONS: dict[str, FunctionSignature] = {
    "print": FunctionSignature(name="print", param_count=1, return_type="void"),
}


@dataclass
class SemanticError:
    message: str
    line: int
    column: int

    def to_dict(self) -> dict:
        return {"message": self.message, "line": self.line, "column": self.column}


@dataclass
class SemanticResult:
    errors: list[SemanticError]
    symbols: list[Symbol]  # every symbol declared anywhere, for the symbol-table view

    def to_dict(self) -> dict:
        return {
            "errors": [e.to_dict() for e in self.errors],
            "symbols": [s.to_dict() for s in self.symbols],
        }


def _is_numeric(type_: str) -> bool:
    return type_ in ("int", "float")


def _compatible(declared_type: str, value_type: str) -> bool:
    """True if a value of `value_type` may be stored in a variable of
    `declared_type`. Exact matches are always fine; the one widening
    rule allowed is assigning an int where a float is expected.
    """
    if value_type == TYPE_ERROR:
        return True
    if declared_type == value_type:
        return True
    return declared_type == "float" and value_type == "int"


class SemanticAnalyzer:
    def __init__(self) -> None:
        self.symbol_table = SymbolTable()
        self.errors: list[SemanticError] = []

    def _error(self, message: str, line: int, column: int) -> None:
        self.errors.append(SemanticError(message, line, column))

    # -- statements -------------------------------------------------------

    def analyze(self, program: Program) -> SemanticResult:
        for stmt in program.statements:
            self._visit_statement(stmt)
        return SemanticResult(errors=self.errors, symbols=self.symbol_table.all_declared)

    def _visit_statement(self, stmt) -> None:
        if isinstance(stmt, VarDecl):
            self._visit_var_decl(stmt)
        elif isinstance(stmt, Assignment):
            self._visit_assignment(stmt)
        elif isinstance(stmt, IfStmt):
            self._visit_if(stmt)
        elif isinstance(stmt, WhileStmt):
            self._visit_while(stmt)
        elif isinstance(stmt, ReturnStmt):
            if stmt.value is not None:
                self._infer_type(stmt.value)
        elif isinstance(stmt, Block):
            self._visit_block(stmt)
        elif isinstance(stmt, ExprStmt):
            self._infer_type(stmt.expr)
        else:
            raise TypeError(f"Unknown statement node: {type(stmt)!r}")

    def _visit_var_decl(self, stmt: VarDecl) -> None:
        if stmt.init is not None:
            init_type = self._infer_type(stmt.init)
            if not _compatible(stmt.var_type, init_type):
                self._error(
                    f"Cannot initialize variable '{stmt.name}' of type "
                    f"'{stmt.var_type}' with a value of type '{init_type}'",
                    stmt.line,
                    stmt.column,
                )
        declared = self.symbol_table.declare(stmt.name, stmt.var_type, stmt.line, stmt.column)
        if not declared:
            self._error(
                f"Variable '{stmt.name}' is already declared in this scope",
                stmt.line,
                stmt.column,
            )

    def _visit_assignment(self, stmt: Assignment) -> None:
        value_type = self._infer_type(stmt.value)
        symbol = self.symbol_table.lookup(stmt.name)
        if symbol is None:
            self._error(f"Undeclared variable '{stmt.name}'", stmt.line, stmt.column)
            return
        if not _compatible(symbol.type, value_type):
            self._error(
                f"Cannot assign a value of type '{value_type}' to variable "
                f"'{stmt.name}' of type '{symbol.type}'",
                stmt.line,
                stmt.column,
            )

    def _visit_if(self, stmt: IfStmt) -> None:
        self._check_condition(stmt.condition)
        self._visit_block(stmt.then_block)
        if stmt.else_block is not None:
            self._visit_block(stmt.else_block)

    def _visit_while(self, stmt: WhileStmt) -> None:
        self._check_condition(stmt.condition)
        self._visit_block(stmt.body)

    def _check_condition(self, condition) -> None:
        condition_type = self._infer_type(condition)
        if condition_type != "bool" and condition_type != TYPE_ERROR:
            self._error(
                f"Condition must be of type 'bool', got '{condition_type}'",
                condition.line,
                condition.column,
            )

    def _visit_block(self, block: Block) -> None:
        self.symbol_table.push_scope()
        for stmt in block.statements:
            self._visit_statement(stmt)
        self.symbol_table.pop_scope()

    # -- expressions ------------------------------------------------------

    def _infer_type(self, expr) -> str:
        if isinstance(expr, Literal):
            return _LITERAL_TYPE_MAP[expr.literal_type]

        if isinstance(expr, Identifier):
            symbol = self.symbol_table.lookup(expr.name)
            if symbol is None:
                self._error(f"Undeclared variable '{expr.name}'", expr.line, expr.column)
                return TYPE_ERROR
            return symbol.type

        if isinstance(expr, UnaryOp):
            return self._infer_unary(expr)

        if isinstance(expr, BinaryOp):
            return self._infer_binary(expr)

        if isinstance(expr, Call):
            return self._infer_call(expr)

        raise TypeError(f"Unknown expression node: {type(expr)!r}")

    def _infer_unary(self, expr: UnaryOp) -> str:
        operand_type = self._infer_type(expr.operand)
        if expr.op == "-":
            if operand_type == TYPE_ERROR or _is_numeric(operand_type):
                return operand_type
            self._error(
                f"Unary '-' requires a numeric operand, got '{operand_type}'",
                expr.line,
                expr.column,
            )
            return TYPE_ERROR
        if expr.op == "!":
            if operand_type == TYPE_ERROR or operand_type == "bool":
                return "bool"
            self._error(
                f"Unary '!' requires a 'bool' operand, got '{operand_type}'",
                expr.line,
                expr.column,
            )
            return TYPE_ERROR
        raise ValueError(f"Unknown unary operator: {expr.op!r}")

    def _infer_binary(self, expr: BinaryOp) -> str:
        left_type = self._infer_type(expr.left)
        right_type = self._infer_type(expr.right)
        if left_type == TYPE_ERROR or right_type == TYPE_ERROR:
            return TYPE_ERROR

        op = expr.op

        if op in _ARITHMETIC_OPS:
            if op == "+" and left_type == "string" and right_type == "string":
                return "string"
            if _is_numeric(left_type) and _is_numeric(right_type):
                return "float" if "float" in (left_type, right_type) else "int"
            self._error(
                f"Operator '{op}' cannot be applied to '{left_type}' and '{right_type}'",
                expr.line,
                expr.column,
            )
            return TYPE_ERROR

        if op in _RELATIONAL_OPS:
            if _is_numeric(left_type) and _is_numeric(right_type):
                return "bool"
            self._error(
                f"Operator '{op}' requires numeric operands, got '{left_type}' and '{right_type}'",
                expr.line,
                expr.column,
            )
            return TYPE_ERROR

        if op in _EQUALITY_OPS:
            if left_type == right_type or (_is_numeric(left_type) and _is_numeric(right_type)):
                return "bool"
            self._error(
                f"Cannot compare '{left_type}' and '{right_type}' with '{op}'",
                expr.line,
                expr.column,
            )
            return TYPE_ERROR

        if op in _LOGICAL_OPS:
            if left_type == "bool" and right_type == "bool":
                return "bool"
            self._error(
                f"Operator '{op}' requires 'bool' operands, got '{left_type}' and '{right_type}'",
                expr.line,
                expr.column,
            )
            return TYPE_ERROR

        raise ValueError(f"Unknown binary operator: {op!r}")

    def _infer_call(self, expr: Call) -> str:
        arg_types = [self._infer_type(arg) for arg in expr.args]

        signature = BUILTIN_FUNCTIONS.get(expr.callee)
        if signature is None:
            self._error(f"Call to undefined function '{expr.callee}'", expr.line, expr.column)
            return TYPE_ERROR

        if len(expr.args) != signature.param_count:
            self._error(
                f"Function '{expr.callee}' expects {signature.param_count} "
                f"argument(s), got {len(expr.args)}",
                expr.line,
                expr.column,
            )
            return TYPE_ERROR

        return signature.return_type


def analyze(program: Program) -> SemanticResult:
    return SemanticAnalyzer().analyze(program)
