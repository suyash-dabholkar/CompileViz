"""
Grammar analysis logic.

Milestone 5 (done): grammar_parser.py parses a user-supplied CFG,
    first_follow.py computes FIRST/FOLLOW sets, ll1_table.py builds the
    LL(1) parsing table and flags conflicts, analyzer.py ties all three
    together into one entry point (analyze_grammar).
"""

from app.grammar.analyzer import analyze_grammar
from app.grammar.grammar_parser import Grammar, GrammarSyntaxError, parse_grammar
from app.grammar.ll1_table import LL1Table, build_ll1_table

__all__ = [
    "Grammar",
    "GrammarSyntaxError",
    "LL1Table",
    "analyze_grammar",
    "build_ll1_table",
    "parse_grammar",
]
