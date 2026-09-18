"""
Tests for Milestone 5's ll1_table.py, and the analyzer.py entry point
that ties parsing, FIRST/FOLLOW, and the table together.
"""

from app.grammar.analyzer import analyze_grammar
from app.grammar.first_follow import compute_first_sets, compute_follow_sets
from app.grammar.grammar_parser import parse_grammar
from app.grammar.ll1_table import build_ll1_table

EXPRESSION_GRAMMAR = """
E  -> T E2
E2 -> + T E2 | eps
T  -> F T2
T2 -> * F T2 | eps
F  -> ( E ) | id
"""


def test_expression_grammar_is_ll1_with_expected_cells():
    grammar = parse_grammar(EXPRESSION_GRAMMAR)
    first = compute_first_sets(grammar)
    follow = compute_follow_sets(grammar, first)
    table = build_ll1_table(grammar, first, follow)

    assert table.is_ll1
    assert table.conflicts == []
    assert table.table[("E", "id")] == [["T", "E2"]]
    assert table.table[("E", "(")] == [["T", "E2"]]
    assert table.table[("E2", "+")] == [["+", "T", "E2"]]
    assert table.table[("E2", ")")] == [[]]  # epsilon, via FOLLOW(E2)
    assert table.table[("E2", "$")] == [[]]
    assert table.table[("F", "id")] == [["id"]]


def test_ambiguous_grammar_produces_a_first_first_conflict():
    # S -> A | B, with both A and B able to start with 'a'.
    grammar = parse_grammar("S -> A | B\nA -> a\nB -> a")
    first = compute_first_sets(grammar)
    follow = compute_follow_sets(grammar, first)
    table = build_ll1_table(grammar, first, follow)

    assert not table.is_ll1
    assert len(table.conflicts) == 1
    conflict = table.conflicts[0]
    assert conflict["non_terminal"] == "S"
    assert conflict["terminal"] == "a"
    assert set(conflict["productions"]) == {"A", "B"}


def test_dangling_else_style_grammar_is_not_ll1():
    # A simplified if/else ambiguity: FIRST/FOLLOW conflict on 'else'.
    grammar_text = """
    Stmt -> if Cond then Stmt Else | other
    Else -> else Stmt | eps
    """
    grammar = parse_grammar(grammar_text)
    first = compute_first_sets(grammar)
    follow = compute_follow_sets(grammar, first)
    table = build_ll1_table(grammar, first, follow)
    assert not table.is_ll1


def test_analyze_grammar_end_to_end_matches_textbook_grammar():
    result = analyze_grammar(EXPRESSION_GRAMMAR)
    assert result["start_symbol"] == "E"
    assert result["first_sets"]["E2"] == sorted(["+", "\u03b5"])
    assert result["follow_sets"]["F"] == sorted(["+", "*", ")", "$"])
    assert result["ll1_table"]["is_ll1"] is True
    assert result["ll1_table"]["conflicts"] == []


def test_analyze_grammar_reports_conflicts_in_dict_form():
    result = analyze_grammar("S -> A | B\nA -> a\nB -> a")
    assert result["ll1_table"]["is_ll1"] is False
    assert len(result["ll1_table"]["conflicts"]) == 1


def test_to_dict_is_json_serializable():
    import json

    result = analyze_grammar(EXPRESSION_GRAMMAR)
    json.dumps(result, ensure_ascii=False)
