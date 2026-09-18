"""
The toy-language compiler pipeline.

Milestone 7 (done): token_specs.py defines the toy language's tokens
    as regexes; lexer.py tokenizes source using the Milestone 2
    direct-method DFA engine, one DFA per token type, with maximal
    munch and error recovery.
Milestone 8 (done): ast_nodes.py defines the AST; parser.py is a
    recursive-descent parser over the lexer's tokens, with syntax
    error recovery.
Milestone 9:  semantic analyzer (symbol table, type checking)
Milestone 10: intermediate code generator (AST -> three-address code)
Milestone 11: optimizer (constant folding, dead code elimination, CSE)
Milestone 12: code generator (TAC -> stack-machine / assembly output)
"""

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
from app.compiler.lexer import LexError, LexResult, Token, tokenize
from app.compiler.parser import ParseError, ParseResult, Parser, parse
from app.compiler.token_specs import KEYWORDS, TOKEN_SPECS

__all__ = [
    "KEYWORDS",
    "TOKEN_SPECS",
    "LexError",
    "LexResult",
    "Token",
    "tokenize",
    "Assignment",
    "BinaryOp",
    "Block",
    "Call",
    "ExprStmt",
    "Identifier",
    "IfStmt",
    "Literal",
    "Program",
    "ReturnStmt",
    "UnaryOp",
    "VarDecl",
    "WhileStmt",
    "Parser",
    "ParseError",
    "ParseResult",
    "parse",
]
