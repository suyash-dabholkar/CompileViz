"""
Automata construction logic.

Milestone 2 (done): direct-method DFA construction (followpos / Aho-Ullman).
    See regex_parser.py for parsing and direct_dfa.py for the algorithm.
Milestone 3: indirect method (Thompson's construction + subset construction)
             and the benchmark comparing both.
Milestone 6: DFA minimization (partition refinement).
"""

from app.automata.direct_dfa import DFA, build_direct_dfa
from app.automata.regex_parser import RegexSyntaxError

__all__ = ["DFA", "build_direct_dfa", "RegexSyntaxError"]
