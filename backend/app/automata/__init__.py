"""
Automata construction logic.

Milestone 2 (done): direct-method DFA construction (followpos / Aho-Ullman).
    See regex_parser.py for parsing and direct_dfa.py for the algorithm.
Milestone 3 (done): indirect method (Thompson's construction in
    thompson_nfa.py + subset construction in subset_construction.py),
    and the benchmark comparing both in benchmark.py.
Milestone 6: DFA minimization (partition refinement).
"""

from app.automata.benchmark import BenchmarkResult, compare_construction_methods
from app.automata.dfa import DFA
from app.automata.direct_dfa import build_direct_dfa
from app.automata.regex_parser import RegexSyntaxError
from app.automata.subset_construction import build_indirect_dfa
from app.automata.thompson_nfa import NFA, build_thompson_nfa

__all__ = [
    "DFA",
    "NFA",
    "BenchmarkResult",
    "RegexSyntaxError",
    "build_direct_dfa",
    "build_indirect_dfa",
    "build_thompson_nfa",
    "compare_construction_methods",
]
