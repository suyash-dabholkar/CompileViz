"""
The single entry point the API (and tests) actually call: parse a
grammar, compute FIRST and FOLLOW, build the LL(1) table, and return
everything as one JSON-friendly dict.
"""

from __future__ import annotations

from app.grammar.first_follow import compute_first_sets, compute_follow_sets
from app.grammar.grammar_parser import parse_grammar
from app.grammar.ll1_table import build_ll1_table


def analyze_grammar(text: str) -> dict:
    """Raises GrammarSyntaxError (from grammar_parser) if `text` is invalid."""
    grammar = parse_grammar(text)
    first = compute_first_sets(grammar)
    follow = compute_follow_sets(grammar, first)
    table = build_ll1_table(grammar, first, follow)

    return {
        "start_symbol": grammar.start_symbol,
        "non_terminals": sorted(grammar.non_terminals),
        "terminals": sorted(grammar.terminals),
        "first_sets": {nt: sorted(first[nt]) for nt in grammar.non_terminals},
        "follow_sets": {nt: sorted(follow[nt]) for nt in grammar.non_terminals},
        "ll1_table": table.to_dict(),
    }
