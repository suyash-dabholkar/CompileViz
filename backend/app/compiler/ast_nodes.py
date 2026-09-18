"""
AST node types produced by parser.py.

Every node carries its source `line` and `column` (from the token that
started it), which Milestone 9's semantic analyzer and later phases use
for error messages, and which the dashboard uses to highlight a node's
source location.

Expression nodes (Literal, Identifier, BinaryOp, UnaryOp, Call) and
statement nodes (VarDecl, Assignment, IfStmt, WhileStmt, ReturnStmt,
Block, ExprStmt) are kept as distinct, explicit dataclasses rather than
one generic "Node" type, so later milestones (semantic analysis, TAC
generation) can pattern-match on type with isinstance() instead of
checking a string tag everywhere.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Union


@dataclass
class Literal:
    value: str  # kept as the raw lexeme; semantic analysis (Milestone 9) converts it
    literal_type: str  # "INT", "FLOAT", "STRING", "BOOL"
    line: int
    column: int

    def to_dict(self) -> dict:
        return {
            "kind": "Literal",
            "value": self.value,
            "literal_type": self.literal_type,
            "line": self.line,
            "column": self.column,
        }


@dataclass
class Identifier:
    name: str
    line: int
    column: int

    def to_dict(self) -> dict:
        return {"kind": "Identifier", "name": self.name, "line": self.line, "column": self.column}


@dataclass
class UnaryOp:
    op: str
    operand: "Expr"
    line: int
    column: int

    def to_dict(self) -> dict:
        return {
            "kind": "UnaryOp",
            "op": self.op,
            "operand": self.operand.to_dict(),
            "line": self.line,
            "column": self.column,
        }


@dataclass
class BinaryOp:
    op: str
    left: "Expr"
    right: "Expr"
    line: int
    column: int

    def to_dict(self) -> dict:
        return {
            "kind": "BinaryOp",
            "op": self.op,
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
            "line": self.line,
            "column": self.column,
        }


@dataclass
class Call:
    callee: str
    args: list["Expr"]
    line: int
    column: int

    def to_dict(self) -> dict:
        return {
            "kind": "Call",
            "callee": self.callee,
            "args": [a.to_dict() for a in self.args],
            "line": self.line,
            "column": self.column,
        }


Expr = Union[Literal, Identifier, UnaryOp, BinaryOp, Call]


@dataclass
class VarDecl:
    var_type: str  # "int" | "float" | "bool" | "string"
    name: str
    init: Optional[Expr]
    line: int
    column: int

    def to_dict(self) -> dict:
        return {
            "kind": "VarDecl",
            "var_type": self.var_type,
            "name": self.name,
            "init": self.init.to_dict() if self.init else None,
            "line": self.line,
            "column": self.column,
        }


@dataclass
class Assignment:
    name: str
    value: Expr
    line: int
    column: int

    def to_dict(self) -> dict:
        return {
            "kind": "Assignment",
            "name": self.name,
            "value": self.value.to_dict(),
            "line": self.line,
            "column": self.column,
        }


@dataclass
class Block:
    statements: list["Stmt"]
    line: int
    column: int

    def to_dict(self) -> dict:
        return {
            "kind": "Block",
            "statements": [s.to_dict() for s in self.statements],
            "line": self.line,
            "column": self.column,
        }


@dataclass
class IfStmt:
    condition: Expr
    then_block: Block
    else_block: Optional[Block]
    line: int
    column: int

    def to_dict(self) -> dict:
        return {
            "kind": "IfStmt",
            "condition": self.condition.to_dict(),
            "then_block": self.then_block.to_dict(),
            "else_block": self.else_block.to_dict() if self.else_block else None,
            "line": self.line,
            "column": self.column,
        }


@dataclass
class WhileStmt:
    condition: Expr
    body: Block
    line: int
    column: int

    def to_dict(self) -> dict:
        return {
            "kind": "WhileStmt",
            "condition": self.condition.to_dict(),
            "body": self.body.to_dict(),
            "line": self.line,
            "column": self.column,
        }


@dataclass
class ReturnStmt:
    value: Optional[Expr]
    line: int
    column: int

    def to_dict(self) -> dict:
        return {
            "kind": "ReturnStmt",
            "value": self.value.to_dict() if self.value else None,
            "line": self.line,
            "column": self.column,
        }


@dataclass
class ExprStmt:
    expr: Expr
    line: int
    column: int

    def to_dict(self) -> dict:
        return {"kind": "ExprStmt", "expr": self.expr.to_dict(), "line": self.line, "column": self.column}


Stmt = Union[VarDecl, Assignment, IfStmt, WhileStmt, ReturnStmt, Block, ExprStmt]


@dataclass
class Program:
    statements: list[Stmt] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"kind": "Program", "statements": [s.to_dict() for s in self.statements]}
