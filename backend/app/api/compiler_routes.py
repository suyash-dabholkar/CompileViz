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
    POST /api/compiler/tac     -> the above, plus the three-address
                                     code listing
    POST /api/compiler/optimize -> the above, plus every optimization
                                     pass's before/after TAC (constant
                                     folding, common subexpression
                                     elimination, dead code elimination)
    POST /api/compiler/codegen -> the above, plus the generated
                                     stack-machine assembly AND the
                                     result of actually running it
                                     (output, final variable values,
                                     or a runtime error), the complete
                                     six-phase pipeline in one call

This is the last phase of the core pipeline; later milestones (the
dashboard integration, inline error highlighting, presets) build on
top of what's here rather than adding new compiler phases.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.compiler.codegen import generate_code
from app.compiler.interpreter import run_program
from app.compiler.lexer import tokenize
from app.compiler.optimizer import optimize as run_optimizer
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


class OptimizeOut(BaseModel):
    ast: dict[str, Any]
    lex_errors: list[LexErrorOut]
    parse_errors: list[ParseErrorOut]
    semantic_errors: list[SemanticErrorOut]
    symbols: list[SymbolOut]
    original: list[TACInstrOut]
    after_constant_folding: list[TACInstrOut]
    after_cse: list[TACInstrOut]
    after_dce: list[TACInstrOut]
    instructions_removed: int


@router.post("/optimize", response_model=OptimizeOut)
def optimize_endpoint(request: SourceRequest) -> dict:
    """Run the full front end, generate TAC, and optimize it
    (Milestone 11): constant folding and propagation, common
    subexpression elimination, then dead code elimination, in that
    order since each pass can expose new opportunities for the next
    one. Returns the TAC after every stage, not just the final result,
    so the dashboard can show a before/after diff for each individual
    optimization, not only the overall effect.
    """
    lex_result = tokenize(request.source)
    parse_result = parse(lex_result.tokens)
    semantic_result = analyze(parse_result.program)
    instructions = generate_tac(parse_result.program)
    optimized = run_optimizer(instructions)
    return {
        "ast": parse_result.program.to_dict(),
        "lex_errors": [e.to_dict() for e in lex_result.errors],
        "parse_errors": [e.to_dict() for e in parse_result.errors],
        "semantic_errors": [e.to_dict() for e in semantic_result.errors],
        "symbols": [s.to_dict() for s in semantic_result.symbols],
        **optimized.to_dict(),
    }


class AssemblyInstrOut(BaseModel):
    op: str
    arg: Optional[str] = None
    arg2: Optional[str] = None
    text: str


class RunResultOut(BaseModel):
    output: list[str]
    variables: dict[str, str]
    steps: int
    runtime_error: Optional[str] = None


class CodegenOut(BaseModel):
    ast: dict[str, Any]
    lex_errors: list[LexErrorOut]
    parse_errors: list[ParseErrorOut]
    semantic_errors: list[SemanticErrorOut]
    symbols: list[SymbolOut]
    original: list[TACInstrOut]
    after_constant_folding: list[TACInstrOut]
    after_cse: list[TACInstrOut]
    after_dce: list[TACInstrOut]
    instructions_removed: int
    assembly: list[AssemblyInstrOut]
    run_result: RunResultOut


@router.post("/codegen", response_model=CodegenOut)
def codegen_endpoint(request: SourceRequest) -> dict:
    """The complete six-phase pipeline in one call: lex, parse,
    semantic analysis, TAC generation, optimization, code generation,
    and then actually running the generated stack-machine code.

    Execution is always attempted, even for a program with semantic
    errors, since seeing what it would actually do (or where it goes
    wrong at runtime) is often exactly what's useful for understanding
    a mistake. The interpreter itself is protected against infinite
    loops (a step cap) and reports any runtime problem (division by
    zero, a variable read before assignment) as a normal result field
    rather than a server error.
    """
    lex_result = tokenize(request.source)
    parse_result = parse(lex_result.tokens)
    semantic_result = analyze(parse_result.program)
    instructions = generate_tac(parse_result.program)
    optimized = run_optimizer(instructions)
    assembly = generate_code(optimized.after_dce)
    run_result = run_program(assembly)
    return {
        "ast": parse_result.program.to_dict(),
        "lex_errors": [e.to_dict() for e in lex_result.errors],
        "parse_errors": [e.to_dict() for e in parse_result.errors],
        "semantic_errors": [e.to_dict() for e in semantic_result.errors],
        "symbols": [s.to_dict() for s in semantic_result.symbols],
        **optimized.to_dict(),
        "assembly": [i.to_dict() for i in assembly],
        "run_result": run_result.to_dict(),
    }
