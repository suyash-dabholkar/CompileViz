"""
Step-trace collection for the teaching layer.

Every algorithm in this project used to be a single pass that returned
only its final answer: build_direct_dfa computed the whole
nullable/firstpos/lastpos table and the complete followpos map in local
variables and then threw both away. That is exactly the material a
student is examined on, so the Tracer below lets an algorithm emit the
intermediate steps as it goes without changing what it returns.

Usage, from inside an algorithm:

    def build_direct_dfa(pattern, *, tracer=None):
        ...
        if tracer:
            tracer.step("regex.position", title=..., explain=..., result=...)

The `if tracer:` guard matters: compare_construction_methods times
build_direct_dfa and the regex playground displays those milliseconds,
so an always-on tracer (even a no-op one) would still evaluate every
`explain` f-string and skew the number on screen. None plus a guard
costs nothing when tracing is off.

One schema serves every tool, so the frontend's step renderers and the
quiz machinery are written once. See docs/ or the plan for the shape;
the short version is that every step carries a `data.result` (the one
thing this step computed) and a fixed-key `highlight` bag of id lists.
"""

from __future__ import annotations

SCHEMA = "compileviz.trace/1"

# Every highlight key is always present, so no frontend renderer needs
# an existence check before mapping over one.
HIGHLIGHT_KEYS = ("nodes", "positions", "states", "edges", "rows", "lines", "chars")


def fmt_set(values) -> str:
    """Format a set the way a textbook does: {1, 2, 3}.

    Used all over the explanation strings, by both construction methods,
    so it lives here rather than in either one of them.
    """
    if not values:
        return "{}"
    return "{" + ", ".join(str(v) for v in sorted(values)) + "}"


def _norm(value):
    """Make a value JSON-safe and stable.

    Sets are the native currency of these algorithms (firstpos, lastpos,
    followpos, epsilon-closures, partition groups), and they serialize
    neither reliably nor in a readable order. Normalizing here instead
    of at every emit site keeps the ~15 call sites to one line each.
    """
    if isinstance(value, (set, frozenset)):
        return sorted(value)
    if isinstance(value, dict):
        return {str(k): _norm(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_norm(v) for v in value]
    return value


class Tracer:
    def __init__(self, tool: str, title: str = "", universe=None, limit: int = 4000):
        self.tool = tool
        self.title = title
        # universe is {"kind": str, "items": [...]}: the finite set a
        # set-valued quiz answer is drawn from (regex positions, DFA
        # states, grammar terminals). It is what makes the quiz layer
        # generic, see _quiz below.
        self.universe = universe
        self.limit = limit
        self.steps: list[dict] = []
        # Whatever the algorithm wants the UI to have alongside the steps
        # (the annotated syntax tree, the position table, the finished
        # DFA). It lives here because the algorithm already holds all of
        # it, and the alternative - having the route recompute it - means
        # a second copy of the algorithm that can drift from the real one.
        self.context: dict = {}
        self.truncated = False
        self._phase: str | None = None
        self.depth = 0

    # -- context the emit sites set up around a group of steps ----------

    def phase(self, name: str) -> None:
        self._phase = name

    def push(self) -> None:
        self.depth += 1

    def pop(self) -> None:
        self.depth = max(0, self.depth - 1)

    # -- the one emit method -------------------------------------------

    def step(
        self,
        kind: str,
        *,
        title: str,
        explain: str,
        result,
        phase: str | None = None,
        node: str | None = None,
        highlight: dict | None = None,
        ask: str | None = None,
        choices: list | None = None,
        **data,
    ) -> None:
        """Record one step.

        `result` is mandatory and holds the single thing this step
        computed. Every quiz is derived from it and every "what changed"
        highlight reads it, so a step without one is a step the UI can't
        teach from.
        """
        if len(self.steps) >= self.limit:
            self.truncated = True
            return

        merged = {key: [] for key in HIGHLIGHT_KEYS}
        for key, value in (highlight or {}).items():
            merged[key] = _norm(value)

        payload = {key: _norm(value) for key, value in data.items()}
        payload["result"] = _norm(result)
        if node is not None:
            payload["node"] = node

        self.steps.append(
            {
                "i": len(self.steps),
                "phase": phase or self._phase or "",
                "kind": kind,
                "depth": self.depth,
                "title": title,
                "explain": explain,
                "data": payload,
                "highlight": merged,
                "quiz": self._quiz(ask, payload["result"], choices),
            }
        )

    def _quiz(self, ask: str | None, answer, choices: list | None) -> dict | None:
        """Build a quiz record from the step's own result.

        The correct answer is already in the trace, so the only per-site
        cost is the question's wording. The leverage is that most steps
        in this app answer "which elements of a known finite set" -
        firstpos, followpos, epsilon-closure, move, partition groups,
        FIRST, FOLLOW - so the student picks from `universe` and grading
        is a list comparison. No distractor generation needed.
        """
        if ask is None:
            return None

        if isinstance(answer, list):
            kind = "set"
        elif isinstance(answer, bool):
            # Checked before int on purpose: bool is an int subclass, and
            # a yes/no step wants two buttons, not a number pad.
            kind = "choice"
            choices = choices or ["yes", "no"]
            answer = "yes" if answer else "no"
        elif isinstance(answer, int):
            kind = "number"
        else:
            kind = "choice"

        if kind == "choice" and not choices:
            raise ValueError(f"quiz {ask!r} has a choice answer but no choices")

        return {
            "question": ask,
            "kind": kind,
            "answer": answer,
            "universe": self.universe["items"]
            if (kind == "set" and self.universe)
            else None,
            "choices": _norm(choices) if choices else None,
        }

    # -- output ---------------------------------------------------------

    def to_dict(self, context: dict | None = None) -> dict:
        return {
            "schema": SCHEMA,
            "tool": self.tool,
            "title": self.title,
            "truncated": self.truncated,
            "universe": self.universe,
            "context": {**self.context, **(context or {})},
            "steps": self.steps,
        }
