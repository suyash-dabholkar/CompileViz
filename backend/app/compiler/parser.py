"""
The parser: recursive descent over the token stream from lexer.py,
producing the AST defined in ast_nodes.py.

Grammar (LL(1) by construction, precedence lowest to highest for
expressions, same shape as the classic expression grammar Milestone 5's
grammar tool already analyzes):

    Program    := Statement*
    Statement  := VarDecl | Assignment | IfStmt | WhileStmt
                | ReturnStmt | Block | ExprStmt
    VarDecl    := ('int'|'float'|'bool'|'string') IDENTIFIER
                  ('=' Expression)? ';'
    Assignment := IDENTIFIER '=' Expression ';'
    IfStmt     := 'if' '(' Expression ')' Block ('else' Block)?
    WhileStmt  := 'while' '(' Expression ')' Block
    ReturnStmt := 'return' Expression? ';'
    Block      := '{' Statement* '}'
    ExprStmt   := Expression ';'

    Expression := LogicalOr
    LogicalOr  := LogicalAnd ('||' LogicalAnd)*
    LogicalAnd := Equality ('&&' Equality)*
    Equality   := Relational (('=='|'!=') Relational)*
    Relational := Additive (('<'|'>'|'<='|'>=') Additive)*
    Additive   := Multiplicative (('+'|'-') Multiplicative)*
    Multiplicative := Unary (('*'|'/') Unary)*
    Unary      := ('!'|'-')? Primary
    Primary    := INT | FLOAT | STRING | 'true' | 'false'
                | IDENTIFIER ('(' ArgList? ')')?
                | '(' Expression ')'
    ArgList    := Expression (',' Expression)*

Syntax errors don't stop the parser. On an unexpected token, a
ParseError is recorded and the parser skips ahead to the next likely
statement boundary (a ';', a '}', or a token that starts a new
statement) before continuing, so one pass can report more than one
syntax error, the same recovery philosophy the lexer uses.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.compiler.ast_nodes import (
    Assignment,
    BinaryOp,
    Block,
    Call,
    Expr,
    ExprStmt,
    IfStmt,
    Identifier,
    Literal,
    Program,
    ReturnStmt,
    Stmt,
    UnaryOp,
    VarDecl,
    WhileStmt,
)
from app.compiler.lexer import Token

VAR_TYPE_KEYWORDS = {"int", "float", "bool", "string"}
STATEMENT_START_KEYWORDS = VAR_TYPE_KEYWORDS | {"if", "while", "return"}

_EQUALITY_OPS = {"EQ", "NE"}
_RELATIONAL_OPS = {"LT", "GT", "LE", "GE"}
_ADDITIVE_OPS = {"PLUS", "MINUS"}
_MULTIPLICATIVE_OPS = {"STAR", "SLASH"}


@dataclass
class ParseError:
    message: str
    line: int
    column: int

    def to_dict(self) -> dict:
        return {"message": self.message, "line": self.line, "column": self.column}


@dataclass
class ParseResult:
    program: Program
    errors: list[ParseError]

    def to_dict(self) -> dict:
        return {"ast": self.program.to_dict(), "errors": [e.to_dict() for e in self.errors]}


class _Recover(Exception):
    """Raised internally to unwind out of a broken statement and let
    the top-level loop resynchronize. Never escapes parse().
    """


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0
        self.errors: list[ParseError] = []

    # -- token stream helpers ------------------------------------------------

    def _peek(self, offset: int = 0) -> Token | None:
        i = self.pos + offset
        return self.tokens[i] if i < len(self.tokens) else None

    def _at_end(self) -> bool:
        return self.pos >= len(self.tokens)

    def _advance(self) -> Token:
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def _check(self, type_: str, value: str | None = None) -> bool:
        token = self._peek()
        if token is None or token.type != type_:
            return False
        return value is None or token.value == value

    def _match(self, type_: str, value: str | None = None) -> Token | None:
        if self._check(type_, value):
            return self._advance()
        return None

    def _expect(self, type_: str, value: str | None = None, what: str | None = None) -> Token:
        token = self._match(type_, value)
        if token is not None:
            return token
        described = what or (f"{value!r}" if value else type_)
        found = self._peek()
        found_desc = f"{found.type} {found.value!r}" if found else "end of input"
        line, column = (found.line, found.column) if found else self._last_position()
        self._error(f"Expected {described} but found {found_desc}", line, column)
        raise _Recover()

    def _last_position(self) -> tuple[int, int]:
        if self.tokens:
            last = self.tokens[-1]
            return last.line, last.column + len(last.value)
        return 1, 1

    def _error(self, message: str, line: int, column: int) -> None:
        self.errors.append(ParseError(message, line, column))

    def _synchronize(self) -> None:
        """Skip tokens until a plausible statement boundary, so parsing
        can resume after a syntax error instead of stopping entirely.
        """
        while not self._at_end():
            token = self._peek()
            if token.type == "SEMICOLON":
                self._advance()
                return
            if token.type == "RBRACE":
                return  # let the caller's Block loop see the '}' and stop
            if token.type == "KEYWORD" and token.value in STATEMENT_START_KEYWORDS:
                return
            if token.type == "LBRACE":
                return
            self._advance()

    # -- grammar --------------------------------------------------------

    def parse_program(self) -> Program:
        statements: list[Stmt] = []
        while not self._at_end():
            stmt = self._parse_statement()
            if stmt is not None:
                statements.append(stmt)
        return Program(statements=statements)

    def _parse_statement(self) -> Stmt | None:
        try:
            token = self._peek()
            if token is None:
                return None
            if token.type == "KEYWORD" and token.value in VAR_TYPE_KEYWORDS:
                return self._parse_var_decl()
            if token.type == "KEYWORD" and token.value == "if":
                return self._parse_if()
            if token.type == "KEYWORD" and token.value == "while":
                return self._parse_while()
            if token.type == "KEYWORD" and token.value == "return":
                return self._parse_return()
            if token.type == "LBRACE":
                return self._parse_block()
            if token.type == "IDENTIFIER" and self._peek(1) is not None and self._peek(1).type == "ASSIGN":
                return self._parse_assignment()
            return self._parse_expr_stmt()
        except _Recover:
            self._synchronize()
            return None

    def _parse_var_decl(self) -> VarDecl:
        type_token = self._advance()  # the type keyword itself
        name_token = self._expect("IDENTIFIER", what="a variable name")
        init = None
        if self._match("ASSIGN"):
            init = self._parse_expression()
        self._expect("SEMICOLON", what="';'")
        return VarDecl(
            var_type=type_token.value,
            name=name_token.value,
            init=init,
            line=type_token.line,
            column=type_token.column,
        )

    def _parse_assignment(self) -> Assignment:
        name_token = self._advance()
        self._expect("ASSIGN", what="'='")
        value = self._parse_expression()
        self._expect("SEMICOLON", what="';'")
        return Assignment(name=name_token.value, value=value, line=name_token.line, column=name_token.column)

    def _parse_if(self) -> IfStmt:
        if_token = self._advance()
        self._expect("LPAREN", what="'('")
        condition = self._parse_expression()
        self._expect("RPAREN", what="')'")
        then_block = self._parse_block()
        else_block = None
        if self._match("KEYWORD", "else"):
            else_block = self._parse_block()
        return IfStmt(
            condition=condition,
            then_block=then_block,
            else_block=else_block,
            line=if_token.line,
            column=if_token.column,
        )

    def _parse_while(self) -> WhileStmt:
        while_token = self._advance()
        self._expect("LPAREN", what="'('")
        condition = self._parse_expression()
        self._expect("RPAREN", what="')'")
        body = self._parse_block()
        return WhileStmt(condition=condition, body=body, line=while_token.line, column=while_token.column)

    def _parse_return(self) -> ReturnStmt:
        return_token = self._advance()
        value = None
        if not self._check("SEMICOLON"):
            value = self._parse_expression()
        self._expect("SEMICOLON", what="';'")
        return ReturnStmt(value=value, line=return_token.line, column=return_token.column)

    def _parse_block(self) -> Block:
        brace_token = self._expect("LBRACE", what="'{'")
        statements: list[Stmt] = []
        while not self._at_end() and not self._check("RBRACE"):
            stmt = self._parse_statement()
            if stmt is not None:
                statements.append(stmt)
        self._expect("RBRACE", what="'}'")
        return Block(statements=statements, line=brace_token.line, column=brace_token.column)

    def _parse_expr_stmt(self) -> ExprStmt:
        expr = self._parse_expression()
        self._expect("SEMICOLON", what="';'")
        return ExprStmt(expr=expr, line=expr.line, column=expr.column)

    # -- expressions, lowest to highest precedence -----------------------

    def _parse_expression(self) -> Expr:
        return self._parse_logical_or()

    def _parse_logical_or(self) -> Expr:
        left = self._parse_logical_and()
        while self._check("OR"):
            op_token = self._advance()
            right = self._parse_logical_and()
            left = BinaryOp("||", left, right, op_token.line, op_token.column)
        return left

    def _parse_logical_and(self) -> Expr:
        left = self._parse_equality()
        while self._check("AND"):
            op_token = self._advance()
            right = self._parse_equality()
            left = BinaryOp("&&", left, right, op_token.line, op_token.column)
        return left

    def _parse_equality(self) -> Expr:
        left = self._parse_relational()
        while self._peek() is not None and self._peek().type in _EQUALITY_OPS:
            op_token = self._advance()
            right = self._parse_relational()
            left = BinaryOp(op_token.value, left, right, op_token.line, op_token.column)
        return left

    def _parse_relational(self) -> Expr:
        left = self._parse_additive()
        while self._peek() is not None and self._peek().type in _RELATIONAL_OPS:
            op_token = self._advance()
            right = self._parse_additive()
            left = BinaryOp(op_token.value, left, right, op_token.line, op_token.column)
        return left

    def _parse_additive(self) -> Expr:
        left = self._parse_multiplicative()
        while self._peek() is not None and self._peek().type in _ADDITIVE_OPS:
            op_token = self._advance()
            right = self._parse_multiplicative()
            left = BinaryOp(op_token.value, left, right, op_token.line, op_token.column)
        return left

    def _parse_multiplicative(self) -> Expr:
        left = self._parse_unary()
        while self._peek() is not None and self._peek().type in _MULTIPLICATIVE_OPS:
            op_token = self._advance()
            right = self._parse_unary()
            left = BinaryOp(op_token.value, left, right, op_token.line, op_token.column)
        return left

    def _parse_unary(self) -> Expr:
        if self._check("NOT") or self._check("MINUS"):
            op_token = self._advance()
            operand = self._parse_unary()
            return UnaryOp(op_token.value, operand, op_token.line, op_token.column)
        return self._parse_primary()

    def _parse_primary(self) -> Expr:
        token = self._peek()
        if token is None:
            line, column = self._last_position()
            self._error("Expected an expression but found end of input", line, column)
            raise _Recover()

        if token.type in ("INT", "FLOAT", "STRING"):
            self._advance()
            return Literal(token.value, token.type, token.line, token.column)

        if token.type == "KEYWORD" and token.value in ("true", "false"):
            self._advance()
            return Literal(token.value, "BOOL", token.line, token.column)

        if token.type == "IDENTIFIER":
            self._advance()
            if self._match("LPAREN"):
                args: list[Expr] = []
                if not self._check("RPAREN"):
                    args.append(self._parse_expression())
                    while self._match("COMMA"):
                        args.append(self._parse_expression())
                self._expect("RPAREN", what="')'")
                return Call(token.value, args, token.line, token.column)
            return Identifier(token.value, token.line, token.column)

        if token.type == "LPAREN":
            self._advance()
            expr = self._parse_expression()
            self._expect("RPAREN", what="')'")
            return expr

        self._error(f"Unexpected token {token.type} {token.value!r} in expression", token.line, token.column)
        raise _Recover()


def parse(tokens: list[Token]) -> ParseResult:
    parser = Parser(tokens)
    program = parser.parse_program()
    return ParseResult(program=program, errors=parser.errors)
