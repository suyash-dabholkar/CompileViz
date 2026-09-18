"""
Tests for benchmark.py. These don't assert specific timing numbers,
timing is inherently machine-dependent, but they do check the benchmark
runs correctly, returns sane data, and that its state counts match what
build_direct_dfa / build_indirect_dfa report on their own.
"""

import json

from app.automata.benchmark import compare_construction_methods
from app.automata.direct_dfa import build_direct_dfa
from app.automata.subset_construction import build_indirect_dfa


def test_benchmark_reports_matching_state_counts():
    result = compare_construction_methods("[a-zA-Z][a-zA-Z0-9]*", runs=5)
    direct_dfa = build_direct_dfa("[a-zA-Z][a-zA-Z0-9]*")
    indirect_dfa = build_indirect_dfa("[a-zA-Z][a-zA-Z0-9]*")
    assert result.direct_state_count == len(direct_dfa.states)
    assert result.indirect_state_count == len(indirect_dfa.states)


def test_benchmark_times_are_positive():
    result = compare_construction_methods("(a|b)*abb", runs=5)
    assert result.direct_time_seconds > 0
    assert result.indirect_time_seconds > 0


def test_benchmark_to_dict_is_json_serializable():
    result = compare_construction_methods("[0-9]+", runs=5)
    json.dumps(result.to_dict())


def test_benchmark_on_textbook_example_matches_known_state_count():
    # (a|b)*abb: the direct method's well-known minimal result is 4 states.
    result = compare_construction_methods("(a|b)*abb", runs=5)
    assert result.direct_state_count == 4
