"""
Compiler pipeline API routes.

Mounted at /api/compiler in app.main, so the full paths are:
    POST /api/compiler/tokenize -> tokens and lexical errors
    POST /api/compiler/parse    -> the AST, plus both lexical and
                                     syntax errors, for a source snippet

Later milestones (semantic analyzer, IR, optimizer, codegen) add their
own endpoints here as each phase lands.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.compiler.lexer import tokenize
from app.compiler.parser import parse

router = APIRouter()


class SourceRequest(BaseModel):
    source: str = Field(..., max_length=10000)


class TokenOut(BaseModel):
    type: str
    value: str
    line: int
    column: int


class LexErrorOut(BaseModel):
    message: str
    line: int
    column: int


class TokenizeOut(BaseModel):
    tokens: list[TokenOut]
    errors: list[LexErrorOut]


class ParseErrorOut(BaseModel):
    message: str
    line: int
    column: int


class ParseOut(BaseModel):
    # The AST's shape is recursive and varies by node kind (see
    # ast_nodes.py's to_dict methods), which isn't a good fit for a
    # single strict Pydantic model, so it's passed through as plain
    # JSON here rather than fully typed.
    ast: dict[str, Any]
    lex_errors: list[LexErrorOut]
    parse_errors: list[ParseErrorOut]


@router.post("/tokenize", response_model=TokenizeOut)
def tokenize_endpoint(request: SourceRequest) -> dict:
    """Tokenize `source`. Unlike the regex endpoints, this never
    returns an HTTP error for bad input, an invalid character in the
    source is a normal, expected outcome of lexing, not a malformed
    request, so it comes back as a 200 with populated `errors`, which
    is exactly what the dashboard's inline error highlighting (a later
    milestone) needs to show every problem in the file at once.
    """
    result = tokenize(request.source)
    return result.to_dict()


@router.post("/parse", response_model=ParseOut)
def parse_endpoint(request: SourceRequest) -> dict:
    """Tokenize and parse `source`, returning the AST plus every
    lexical and syntax error found. Parsing still runs even when the
    lexer found errors, since the parser's own error recovery can
    often make sense of the tokens on either side of a bad character.
    """
    lex_result = tokenize(request.source)
    parse_result = parse(lex_result.tokens)
    return {
        "ast": parse_result.program.to_dict(),
        "lex_errors": [e.to_dict() for e in lex_result.errors],
        "parse_errors": [e.to_dict() for e in parse_result.errors],
    }
