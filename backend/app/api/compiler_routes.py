"""
Compiler pipeline API routes.

Mounted at /api/compiler in app.main, so the full path is:
    POST /api/compiler/tokenize -> tokens and lexical errors for a
                                     toy-language source snippet

Later milestones (parser, semantic analyzer, IR, optimizer, codegen)
add their own endpoints here as each phase lands.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.compiler.lexer import tokenize

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
