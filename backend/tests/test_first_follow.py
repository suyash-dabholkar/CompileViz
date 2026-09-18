"""
Tests for Milestone 5's first_follow.py.

The main test reproduces the classic expression-grammar example (the
same one used throughout the Dragon Book for this exact algorithm) and
checks our computed FIRST and FOLLOW sets match the textbook's known
correct answer exactly, the same style of validation as the DFA tests
matching the Aho-Ullman example in Milestone 2.
"""

from app.grammar.first_follow import compute_first_sets, compute_follow_sets
from app.grammar.grammar_parser import parse_grammar

EXPRESSION_GRAMMAR = """
E  -> T E2
E2 -> + T E2 | eps
T  -> F T2
T2 -> * F T2 | eps
F  -> ( E ) | id
"""


def test_first_sets_match_textbook_expression_grammar():
    grammar = parse_grammar(EXPRESSION_GRAMMAR)
    first = compute_first_sets(grammar)

    assert first["E"] == {"(", "id"}
    assert first["T"] == {"(", "id"}
    assert first["F"] == {"(", "id"}
    assert first["E2"] == {"+", "\u03b5"}
    assert first["T2"] == {"*", "\u03b5"}


def test_follow_sets_match_textbook_expression_grammar():
    grammar = parse_grammar(EXPRESSION_GRAMMAR)
    first = compute_first_sets(grammar)
    follow = compute_follow_sets(grammar, first)

    assert follow["E"] == {")", "$"}
    assert follow["E2"] == {")", "$"}
    assert follow["T"] == {"+", ")", "$"}
    assert follow["T2"] == {"+", ")", "$"}
    assert follow["F"] == {"+", "*", ")", "$"}


def test_left_recursive_grammar_terminates_and_is_correct():
    # A -> A a | b  is classic left recursion. The iterative fixed-point
    # algorithm must not infinite-loop on this, and FIRST(A) should
    # still correctly come out as just {b}.
    grammar = parse_grammar("A -> A a | b")
    first = compute_first_sets(grammar)
    assert first["A"] == {"b"}


def test_nullable_chain_propagates_epsilon():
    # S -> A B, A -> eps, B -> eps  means S itself must be nullable too.
    grammar = parse_grammar("S -> A B\nA -> eps\nB -> eps")
    first = compute_first_sets(grammar)
    assert first["S"] == {"\u03b5"}


def test_follow_of_start_symbol_always_includes_end_marker():
    grammar = parse_grammar("S -> a")
    first = compute_first_sets(grammar)
    follow = compute_follow_sets(grammar, first)
    assert "$" in follow["S"]
