"""
Grammar analysis API routes.

Mounted at /api/grammar in app.main, so the full path is:
    POST /api/grammar/analyze -> FIRST sets, FOLLOW sets, and the LL(1)
                                  table (with conflicts) for a
                                  user-supplied grammar
    POST /api/grammar/steps   -> the same analysis, but step by step:
                                  each fixed-point sweep and each row of
                                  the table, for the teaching UI
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.trace_schema import TraceOut
from app.grammar import GrammarSyntaxError, analyze_grammar
from app.trace import Tracer

router = APIRouter()


class GrammarRequest(BaseModel):
    grammar: str = Field(..., min_length=1, max_length=4000)


class ConflictOut(BaseModel):
    non_terminal: str
    terminal: str
    productions: list[str]


class LL1TableOut(BaseModel):
    non_terminals: list[str]
    terminals: list[str]
    is_ll1: bool
    table: dict[str, dict[str, list[str]]]
    conflicts: list[ConflictOut]


class GrammarAnalysisOut(BaseModel):
    start_symbol: str
    non_terminals: list[str]
    terminals: list[str]
    first_sets: dict[str, list[str]]
    follow_sets: dict[str, list[str]]
    ll1_table: LL1TableOut


@router.post("/analyze", response_model=GrammarAnalysisOut)
def analyze_grammar_endpoint(request: GrammarRequest) -> dict:
    try:
        return analyze_grammar(request.grammar)
    except GrammarSyntaxError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/steps", response_model=TraceOut)
def grammar_steps_endpoint(request: GrammarRequest) -> dict:
    """The teaching counterpart to /analyze.

    /analyze answers "what are the sets"; this answers "how were they
    found" - which production grew which set on which sweep, why the
    loop stops, and which lookaheads select each production.
    """
    tracer = Tracer(tool="grammar.ll1", title="FIRST, FOLLOW and the LL(1) table")
    try:
        analyze_grammar(request.grammar, tracer=tracer)
    except GrammarSyntaxError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return tracer.to_dict()
