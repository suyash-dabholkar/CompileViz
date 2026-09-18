"""
Tests for Milestone 5's grammar_parser.py.
"""

import pytest

from app.grammar.grammar_parser import GrammarSyntaxError, parse_grammar


def test_parses_simple_grammar():
    grammar = parse_grammar("S -> a S | b")
    assert grammar.start_symbol == "S"
    assert grammar.non_terminals == {"S"}
    assert grammar.terminals == {"a", "b"}
    assert ["a", "S"] in grammar.productions["S"]
    assert ["b"] in grammar.productions["S"]


def test_start_symbol_is_first_lhs_seen():
    grammar = parse_grammar("A -> B\nB -> b")
    assert grammar.start_symbol == "A"


def test_multiple_lines_for_same_lhs_are_merged():
    grammar = parse_grammar("S -> a\nS -> b")
    assert grammar.productions["S"] == [["a"], ["b"]]


def test_epsilon_token_variants_all_become_empty_production():
    for token in ["\u03b5", "eps", "epsilon", "EPS", "Epsilon"]:
        grammar = parse_grammar(f"S -> {token}")
        assert grammar.productions["S"] == [[]]


def test_blank_right_hand_side_is_epsilon():
    grammar = parse_grammar("S -> ")
    assert grammar.productions["S"] == [[]]


def test_supports_double_colon_equals_arrow():
    grammar = parse_grammar("S ::= a")
    assert grammar.productions["S"] == [["a"]]


def test_undefined_symbol_becomes_a_terminal():
    grammar = parse_grammar("S -> a b")
    assert grammar.terminals == {"a", "b"}
    assert grammar.non_terminals == {"S"}


def test_rejects_empty_grammar():
    with pytest.raises(GrammarSyntaxError):
        parse_grammar("")


def test_rejects_missing_arrow():
    with pytest.raises(GrammarSyntaxError):
        parse_grammar("S a b")


def test_rejects_missing_left_hand_side():
    with pytest.raises(GrammarSyntaxError):
        parse_grammar("-> a b")
