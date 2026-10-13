"""
The single entry point the API (and tests) actually call: parse a
grammar, compute FIRST and FOLLOW, build the LL(1) table, and return
everything as one JSON-friendly dict.
"""

from __future__ import annotations

from app.grammar.first_follow import compute_first_sets, compute_follow_sets
from app.grammar.grammar_parser import END_MARKER, EPSILON, parse_grammar
from app.grammar.ll1_table import build_ll1_table


def analyze_grammar(text: str, *, tracer=None) -> dict:
    """Raises GrammarSyntaxError (from grammar_parser) if `text` is invalid.

    Pass a `tracer` (app.trace.Tracer) to record the FIRST and FOLLOW
    fixed points and the table being filled. The returned dict is the
    same either way, and the tracer also comes back carrying it as
    `context`, so the route does not recompute anything.
    """
    grammar = parse_grammar(text)

    if tracer:
        # Every set-valued answer here is a set of terminals, plus two
        # symbols that are not terminals but do turn up in the answers:
        # epsilon, which FIRST can contain, and the end marker, which
        # FOLLOW can. Leaving either out makes those questions
        # unanswerable, since the quiz offers exactly this list to pick
        # from.
        tracer.universe = {
            "kind": "terminal",
            "items": sorted(grammar.terminals) + [EPSILON, END_MARKER],
        }

    first = compute_first_sets(grammar, tracer=tracer)
    follow = compute_follow_sets(grammar, first, tracer=tracer)
    table = build_ll1_table(grammar, first, follow, tracer=tracer)

    result = {
        "start_symbol": grammar.start_symbol,
        "non_terminals": sorted(grammar.non_terminals),
        "terminals": sorted(grammar.terminals),
        "first_sets": {nt: sorted(first[nt]) for nt in grammar.non_terminals},
        "follow_sets": {nt: sorted(follow[nt]) for nt in grammar.non_terminals},
        "ll1_table": table.to_dict(),
    }

    if tracer:
        tracer.context.update(grammar=text, **result)

    return result
