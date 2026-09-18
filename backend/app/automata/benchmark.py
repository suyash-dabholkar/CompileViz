"""
Benchmark: direct method vs. indirect method.

This is the empirical result the report's Phase 1 benchmark section is
built on. For a given regex, it builds the DFA both ways and reports:
  - how many states each one produced
  - how long each construction took, averaged over several runs to
    smooth out timing noise (a single run of microsecond-scale code is
    not a reliable measurement on its own)

A note on complexity, worth keeping in mind rather than overclaiming in
the report: the direct method always produces at most (n + 1) DFA states
for a regex with n positions, since every state is a subset of positions
that's already capped at that size. The indirect method's Thompson NFA
has O(n) states, but subset construction can in the worst case blow that
up to as many as 2^n DFA states, since a DFA state is a subset of NFA
states. In practice, for the kind of small token-defining regexes this
project actually uses, both methods tend to land on similar, small state
counts, but the direct method's bound is the tighter, guaranteed one.
That empirical closeness (rather than a dramatic blowup) is itself worth
reporting honestly.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from app.automata.direct_dfa import build_direct_dfa
from app.automata.subset_construction import build_indirect_dfa


@dataclass
class BenchmarkResult:
    pattern: str
    direct_state_count: int
    indirect_state_count: int
    direct_time_seconds: float
    indirect_time_seconds: float
    runs: int

    def to_dict(self) -> dict:
        return {
            "pattern": self.pattern,
            "runs": self.runs,
            "direct_method": {
                "state_count": self.direct_state_count,
                "avg_build_time_seconds": self.direct_time_seconds,
            },
            "indirect_method": {
                "state_count": self.indirect_state_count,
                "avg_build_time_seconds": self.indirect_time_seconds,
            },
            "state_count_difference": self.indirect_state_count - self.direct_state_count,
        }


def _time_construction(build_fn, pattern: str, runs: int) -> float:
    """Average wall-clock time of calling build_fn(pattern), over `runs`
    repetitions. Uses perf_counter, the recommended tool for measuring
    short durations in Python.
    """
    start = time.perf_counter()
    for _ in range(runs):
        build_fn(pattern)
    elapsed = time.perf_counter() - start
    return elapsed / runs


def compare_construction_methods(pattern: str, runs: int = 200) -> BenchmarkResult:
    """Build `pattern` via both methods and report state count and
    average build time for each.

    Raises RegexSyntaxError (from regex_parser) if `pattern` is invalid,
    the same way both individual build functions do.
    """
    direct_dfa = build_direct_dfa(pattern)
    indirect_dfa = build_indirect_dfa(pattern)

    direct_time = _time_construction(build_direct_dfa, pattern, runs)
    indirect_time = _time_construction(build_indirect_dfa, pattern, runs)

    return BenchmarkResult(
        pattern=pattern,
        direct_state_count=len(direct_dfa.states),
        indirect_state_count=len(indirect_dfa.states),
        direct_time_seconds=direct_time,
        indirect_time_seconds=indirect_time,
        runs=runs,
    )
