"""
Regex playground API routes.

These wrap the pure Python engines in app.automata (Milestones 2 and 3)
with HTTP endpoints the frontend can call. This module deliberately has
no algorithm logic of its own, it only validates input, calls into
app.automata, translates errors into proper HTTP responses, and shapes
the output as JSON.

Mounted at /api/regex in app.main, so the full paths are:
    POST /api/regex/direct     -> DFA via the direct (followpos) method
    POST /api/regex/indirect   -> DFA via the indirect (Thompson + subset) method
    POST /api/regex/thompson   -> the raw NFA, before subset construction
    POST /api/regex/match      -> test one string against one pattern
    POST /api/regex/compare    -> the Milestone 3 benchmark, both methods at once
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.automata import (
    RegexSyntaxError,
    build_direct_dfa,
    build_indirect_dfa,
    build_thompson_nfa,
    compare_construction_methods,
)
from app.automata.minimization import minimize_dfa

router = APIRouter()


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class RegexRequest(BaseModel):
    pattern: str = Field(..., min_length=1, max_length=200)


class MatchRequest(BaseModel):
    pattern: str = Field(..., min_length=1, max_length=200)
    text: str = Field(..., max_length=1000)
    method: Literal["direct", "indirect"] = "direct"


class CompareRequest(BaseModel):
    pattern: str = Field(..., min_length=1, max_length=200)
    # Capped well below the library default (200): this runs synchronously
    # inside a single HTTP request, and some patterns (wide character
    # classes especially) make the indirect method slow enough that a
    # high run count would make the endpoint feel sluggish in the UI.
    # 10 runs keeps even the worst-case pattern (a wide character class)
    # under ~4 seconds while still smoothing out timing noise.
    runs: int = Field(default=10, ge=1, le=50)


class MinimizeRequest(BaseModel):
    pattern: str = Field(..., min_length=1, max_length=200)
    method: Literal["direct", "indirect"] = "indirect"


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class DFATransitionOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    from_: int = Field(..., alias="from")
    symbol: str
    to: int


class DFAOut(BaseModel):
    start: int
    accepting: list[int]
    num_states: int
    alphabet: list[str]
    states: list[list[int]]
    transitions: list[DFATransitionOut]


class NFATransitionOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    from_: int = Field(..., alias="from")
    symbol: str
    to: int


class NFAOut(BaseModel):
    start: int
    accept: int
    num_states: int
    alphabet: list[str]
    transitions: list[NFATransitionOut]


class MatchOut(BaseModel):
    pattern: str
    text: str
    method: str
    matches: bool


class MethodStatsOut(BaseModel):
    state_count: int
    avg_build_time_seconds: float


class CompareOut(BaseModel):
    pattern: str
    runs: int
    direct_method: MethodStatsOut
    indirect_method: MethodStatsOut
    state_count_difference: int


class MinimizeOut(BaseModel):
    pattern: str
    method: str
    original: DFAOut
    minimized: DFAOut
    state_mapping: dict[str, int]  # original state index (as string) -> minimized state index
    partition_trace: list[list[list[int]]]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/direct", response_model=DFAOut)
def direct_dfa_endpoint(request: RegexRequest) -> dict:
    """Build a DFA via the direct (followpos) method."""
    try:
        dfa = build_direct_dfa(request.pattern)
    except RegexSyntaxError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return dfa.to_dict()


@router.post("/indirect", response_model=DFAOut)
def indirect_dfa_endpoint(request: RegexRequest) -> dict:
    """Build a DFA via the indirect method (Thompson + subset construction)."""
    try:
        dfa = build_indirect_dfa(request.pattern)
    except RegexSyntaxError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return dfa.to_dict()


@router.post("/thompson", response_model=NFAOut)
def thompson_nfa_endpoint(request: RegexRequest) -> dict:
    """Build just the Thompson NFA, before subset construction. The
    frontend uses this for the "here's the messy first draft" half of
    the side-by-side animation.
    """
    try:
        nfa = build_thompson_nfa(request.pattern)
    except RegexSyntaxError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return nfa.to_dict()


@router.post("/match", response_model=MatchOut)
def match_endpoint(request: MatchRequest) -> dict:
    """Test whether `text` matches `pattern`, using whichever method is
    requested. Since both methods are proven equivalent (see
    tests/test_indirect_dfa.py), the result is the same either way,
    this exists so the playground UI can let the user try their own
    strings without rebuilding both DFAs, and for the odd case where
    seeing that both methods agree on a specific input is the point.
    """
    build_fn = build_direct_dfa if request.method == "direct" else build_indirect_dfa
    try:
        dfa = build_fn(request.pattern)
    except RegexSyntaxError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "pattern": request.pattern,
        "text": request.text,
        "method": request.method,
        "matches": dfa.match(request.text),
    }


@router.post("/compare", response_model=CompareOut)
def compare_endpoint(request: CompareRequest) -> dict:
    """Run the Milestone 3 benchmark: build the DFA both ways and report
    state count and average build time for each.
    """
    try:
        result = compare_construction_methods(request.pattern, runs=request.runs)
    except RegexSyntaxError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result.to_dict()


@router.post("/minimize", response_model=MinimizeOut)
def minimize_endpoint(request: MinimizeRequest) -> dict:
    """Build a DFA via the requested method, then minimize it with
    partition refinement (Milestone 6). Defaults to the indirect method
    since that's the one that actually benefits from minimization, the
    direct method is already minimal by construction, minimizing it is
    a no-op that's still useful as a "see, nothing changes" check.
    """
    build_fn = build_direct_dfa if request.method == "direct" else build_indirect_dfa
    try:
        dfa = build_fn(request.pattern)
    except RegexSyntaxError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result = minimize_dfa(dfa)
    return {
        "pattern": request.pattern,
        "method": request.method,
        "original": dfa.to_dict(),
        "minimized": result.minimized.to_dict(),
        "state_mapping": {str(k): v for k, v in result.state_mapping.items()},
        "partition_trace": result.partition_trace,
    }
