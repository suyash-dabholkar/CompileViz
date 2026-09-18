"""
Tests for the Thompson NFA builder itself, separate from the DFA it
eventually produces (that equivalence is tested in test_indirect_dfa.py).
These tests check the NFA's structure directly: state counts, epsilon
transitions, and that epsilon_closure/move behave correctly.
"""

from app.automata.subset_construction import epsilon_closure, move
from app.automata.thompson_nfa import EPSILON, build_thompson_nfa


def test_single_literal_has_two_states_and_one_transition():
    nfa = build_thompson_nfa("a")
    assert nfa.num_states == 2
    assert nfa.transitions[(nfa.start, "a")] == {nfa.accept}


def test_concatenation_links_fragments_with_epsilon():
    nfa = build_thompson_nfa("ab")
    # Every Concat introduces exactly one epsilon-transition joining the
    # two fragments, so ab should have exactly one epsilon-transition.
    epsilon_transitions = [
        (frm, targets) for (frm, sym), targets in nfa.transitions.items() if sym is EPSILON
    ]
    assert len(epsilon_transitions) == 1


def test_union_branches_and_joins():
    nfa = build_thompson_nfa("a|b")
    closure = epsilon_closure({nfa.start}, nfa.transitions)
    # From the start, epsilon-closure should reach both literal fragments'
    # start states, meaning at least 3 states are visible before consuming
    # any input (branch point + both literal starts).
    assert len(closure) >= 3


def test_star_allows_skipping_the_loop():
    nfa = build_thompson_nfa("a*")
    closure = epsilon_closure({nfa.start}, nfa.transitions)
    # a* must accept the empty string, so the accept state should be
    # reachable via epsilon-transitions alone from the start.
    assert nfa.accept in closure


def test_move_then_closure_advances_correctly():
    nfa = build_thompson_nfa("ab")
    start_closure = epsilon_closure({nfa.start}, nfa.transitions)
    after_a = move(start_closure, "a", nfa.transitions)
    assert after_a  # consuming 'a' should move to at least one state
    after_a_closure = epsilon_closure(after_a, nfa.transitions)
    after_ab = move(after_a_closure, "b", nfa.transitions)
    after_ab_closure = epsilon_closure(after_ab, nfa.transitions)
    assert nfa.accept in after_ab_closure


def test_alphabet_excludes_epsilon():
    nfa = build_thompson_nfa("[a-c]")
    assert set(nfa.alphabet) == {"a", "b", "c"}


def test_to_dict_is_json_serializable():
    import json

    nfa = build_thompson_nfa("(a|b)*abb")
    json.dumps(nfa.to_dict())
