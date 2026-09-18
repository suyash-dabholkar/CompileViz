"""
Tests for Milestone 6's minimize_dfa (app/automata/minimization.py).

The strongest tests here cross-validate against Milestones 2 and 3:
minimizing the INDIRECT method's DFA should always land on exactly the
same state count as the DIRECT method's already-minimal DFA for the
same pattern, since the minimal DFA for a given regular language is
unique (up to renaming states). This is a much stronger check than
just "the algorithm ran without crashing".
"""

from app.automata.direct_dfa import build_direct_dfa
from app.automata.minimization import minimize_dfa
from app.automata.subset_construction import build_indirect_dfa


def test_minimizing_indirect_dfa_matches_direct_method_state_count():
    for pattern in ["(a|b)*abb", "[a-zA-Z][a-zA-Z0-9]*", "[0-9]+", "a(b|c)*d"]:
        direct_dfa = build_direct_dfa(pattern)
        indirect_dfa = build_indirect_dfa(pattern)
        result = minimize_dfa(indirect_dfa)
        assert len(result.minimized.states) == len(direct_dfa.states), pattern


def test_minimized_dfa_accepts_and_rejects_the_same_strings():
    indirect_dfa = build_indirect_dfa("(a|b)*abb")
    result = minimize_dfa(indirect_dfa)

    test_strings = ["abb", "aabb", "babb", "ab", "abbb", "", "a", "bb", "aaabb"]
    for s in test_strings:
        assert result.minimized.match(s) == indirect_dfa.match(s), s


def test_already_minimal_dfa_stays_the_same_size():
    direct_dfa = build_direct_dfa("(a|b)*abb")  # already minimal, 4 states
    result = minimize_dfa(direct_dfa)
    assert len(result.minimized.states) == len(direct_dfa.states)


def test_state_mapping_covers_every_original_state():
    indirect_dfa = build_indirect_dfa("(a|b)*abb")
    result = minimize_dfa(indirect_dfa)
    assert set(result.state_mapping.keys()) == set(range(len(indirect_dfa.states)))


def test_state_mapping_groups_equivalent_states_together():
    indirect_dfa = build_indirect_dfa("(a|b)*abb")
    result = minimize_dfa(indirect_dfa)
    # Two of the 5 indirect-method states must merge into the same
    # minimized state, since it collapses from 5 states down to 4.
    grouped = {}
    for original, minimized_state in result.state_mapping.items():
        grouped.setdefault(minimized_state, []).append(original)
    group_sizes = sorted(len(v) for v in grouped.values())
    assert group_sizes == [1, 1, 1, 2]


def test_partition_trace_starts_with_accept_nonaccept_split_and_ends_stable():
    indirect_dfa = build_indirect_dfa("(a|b)*abb")
    result = minimize_dfa(indirect_dfa)

    first_round = result.partition_trace[0]
    # The very first round is exactly the accepting/non-accepting split.
    accepting_states = set(indirect_dfa.accepting)
    matching_groups = [g for g in first_round if set(g) == accepting_states]
    assert len(matching_groups) == 1

    # The trace must stabilize: the last two rounds should be identical
    # (that's what "no more splits" means).
    assert result.partition_trace[-1] == result.partition_trace[-2]


def test_minimized_dfa_to_dict_is_json_serializable():
    import json

    indirect_dfa = build_indirect_dfa("[0-9]+")
    result = minimize_dfa(indirect_dfa)
    json.dumps(result.minimized.to_dict())
    json.dumps(result.partition_trace)
