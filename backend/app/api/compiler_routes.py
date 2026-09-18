"""
Compiler pipeline API routes.

Mounted at /api/compiler in app.main, so the full paths are:
    POST /api/compiler/tokenize -> tokens and lexical errors
    POST /api/compiler/parse    -> the AST, plus both lexical and
                                     syntax errors, for a source snippet
    POST /api/compiler/analyze -> the above, plus the symbol table and
                                     semantic errors (type checking,
                                     undeclared variables, redeclaration,
                                     call arity)

Later milestones (IR, optimizer, codegen) add their own endpoints here
as each phase lands.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.compiler.lexer import tokenize
from app.compiler.parser import parse
from app.compiler.semantic_analyzer import analyze
from app.compiler.tac_generator import generate_tac

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


class SemanticErrorOut(BaseModel):
    message: str
    line: int
    column: int


class SymbolOut(BaseModel):
    name: str
    type: str
    line: int
    column: int
    scope_depth: int


class AnalyzeOut(BaseModel):
    ast: dict[str, Any]
    lex_errors: list[LexErrorOut]
    parse_errors: list[ParseErrorOut]
    semantic_errors: list[SemanticErrorOut]
    symbols: list[SymbolOut]


@router.post("/analyze", response_model=AnalyzeOut)
def analyze_endpoint(request: SourceRequest) -> dict:
    """Run the full front end, lex, parse, and semantic analysis, on
    `source`. Semantic analysis still runs over whatever AST the
    parser managed to build, even if the lexer or parser hit errors,
    since a program with one syntax error elsewhere can still have
    plenty of type-correct code worth checking.
    """
    lex_result = tokenize(request.source)
    parse_result = parse(lex_result.tokens)
    semantic_result = analyze(parse_result.program)
    return {
        "ast": parse_result.program.to_dict(),
        "lex_errors": [e.to_dict() for e in lex_result.errors],
        "parse_errors": [e.to_dict() for e in parse_result.errors],
        "semantic_errors": [e.to_dict() for e in semantic_result.errors],
        "symbols": [s.to_dict() for s in semantic_result.symbols],
    }


class TACInstrOut(BaseModel):
    op: str
    arg1: Optional[str] = None
    arg2: Optional[str] = None
    result: Optional[str] = None
    text: str


class GenerateTacOut(BaseModel):
    ast: dict[str, Any]
    lex_errors: list[LexErrorOut]
    parse_errors: list[ParseErrorOut]
    semantic_errors: list[SemanticErrorOut]
    symbols: list[SymbolOut]
    tac: list[TACInstrOut]


@router.post("/tac", response_model=GenerateTacOut)
def tac_endpoint(request: SourceRequest) -> dict:
    """Run the full front end plus three-address code generation on
    `source`. TAC is generated from whatever AST the parser produced
    regardless of semantic errors, so the dashboard can still show
    what the intermediate code would look like even for a program
    that doesn't fully type-check, useful for seeing the effect of a
    single mistake without losing the rest of the picture.
    """
    lex_result = tokenize(request.source)
    parse_result = parse(lex_result.tokens)
    semantic_result = analyze(parse_result.program)
    instructions = generate_tac(parse_result.program)
    return {
        "ast": parse_result.program.to_dict(),
        "lex_errors": [e.to_dict() for e in lex_result.errors],
        "parse_errors": [e.to_dict() for e in parse_result.errors],
        "semantic_errors": [e.to_dict() for e in semantic_result.errors],
        "symbols": [s.to_dict() for s in semantic_result.symbols],
        "tac": [i.to_dict() for i in instructions],
    }
