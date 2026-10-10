"""
The response model every step-trace endpoint shares.

Lives in its own module rather than in app/trace.py so that the trace
core stays free of FastAPI and Pydantic: the automata and compiler
packages import it, and they are deliberately plain Python so they can
be unit tested (and reused) without pulling in a web framework.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TraceOut(BaseModel):
    """One step trace, in the shape every tool's trace shares.

    Deliberately loose about `context` and `steps`: a step's `data`
    holds whatever that particular algorithm computed, so pinning it
    down here would mean a new model per step kind for no gain. Same
    reasoning as ParseOut.ast in compiler_routes.py. The invariants the
    frontend actually relies on (every step has a `data.result`, every
    `highlight` key is present, every `explain` is non-empty) are
    enforced in app/trace.py and checked in tests/test_trace.py.
    """

    model_config = ConfigDict(populate_by_name=True)
    # `schema` shadows a BaseModel attribute, so it follows the same
    # alias pattern DFATransitionOut already uses for `from`.
    schema_: str = Field(..., alias="schema")
    tool: str
    title: str
    truncated: bool
    universe: dict[str, Any] | None
    context: dict[str, Any]
    steps: list[dict[str, Any]]
