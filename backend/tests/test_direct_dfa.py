"""
Tests for Milestone 2: the direct-method (followpos) DFA engine.

Organized in two parts:
  - parser-level tests, checking the AST is built correctly and rejects
    invalid input
  - DFA-level tests, checking build_direct_dfa produces a DFA that
    accepts and rejects the right strings

The DFA tests are the ones that matter most for the report: they prove
the direct method actually recognizes the same language the regex
describes, without ever going through an NFA.
"""

import pytest

from app.automata.direct_dfa import build_direct_dfa
from app.automata.regex_parser import RegexSyntaxError, parse_regex


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------

def test_parse_literal():
    parse_regex("a")  # should not raise


def test_parse_rejects_empty_pattern():
    with pytest.raises(RegexSyntaxError):
        parse_regex("")


def test_parse_rejects_unbalanced_parens():
    with pytest.raises(RegexSyntaxError):
        parse_regex("(a|b")


def test_parse_rejects_unterminated_char_class():
    with pytest.raises(RegexSyntaxError):
        parse_regex("[a-z")


def test_parse_rejects_dangling_escape():
    with pytest.raises(RegexSyntaxError):
        parse_regex("a\\")


def test_parse_rejects_negated_char_class():
    with pytest.raises(RegexSyntaxError):
        parse_regex("[^abc]")


# ---------------------------------------------------------------------------
# DFA tests: literals, concatenation, union
# ---------------------------------------------------------------------------

def test_single_literal():
    dfa = build_direct_dfa("a")
    assert dfa.match("a")
    assert not dfa.match("b")
    assert not dfa.match("")
    assert not dfa.match("aa")


def test_concatenation():
    dfa = build_direct_dfa("ab")
    assert dfa.match("ab")
    assert not dfa.match("a")
    assert not dfa.match("ba")
    assert not dfa.match("abc")


def test_union():
    dfa = build_direct_dfa("a|b")
    assert dfa.match("a")
    assert dfa.match("b")
    assert not dfa.match("c")
    assert not dfa.match("ab")


# ---------------------------------------------------------------------------
# DFA tests: star, plus, optional
# ---------------------------------------------------------------------------

def test_star_matches_zero_or_more():
    dfa = build_direct_dfa("a*")
    assert dfa.match("")
    assert dfa.match("a")
    assert dfa.match("aaaa")
    assert not dfa.match("b")
    assert not dfa.match("aab")


def test_plus_requires_at_least_one():
    dfa = build_direct_dfa("a+")
    assert not dfa.match("")
    assert dfa.match("a")
    assert dfa.match("aaaa")
    assert not dfa.match("aab")


def test_optional_matches_zero_or_one():
    dfa = build_direct_dfa("a?")
    assert dfa.match("")
    assert dfa.match("a")
    assert not dfa.match("aa")


# ---------------------------------------------------------------------------
# DFA tests: grouping, character classes
# ---------------------------------------------------------------------------

def test_grouping_changes_precedence():
    dfa = build_direct_dfa("(a|b)c")
    assert dfa.match("ac")
    assert dfa.match("bc")
    assert not dfa.match("a")
    assert not dfa.match("abc")


def test_char_class_literal_set():
    dfa = build_direct_dfa("[abc]")
    assert dfa.match("a")
    assert dfa.match("b")
    assert dfa.match("c")
    assert not dfa.match("d")
    assert not dfa.match("")


def test_char_class_range():
    dfa = build_direct_dfa("[a-c]")
    assert dfa.match("a")
    assert dfa.match("c")
    assert not dfa.match("d")


# ---------------------------------------------------------------------------
# DFA tests: realistic token definitions, the actual use case for this engine
# ---------------------------------------------------------------------------

def test_identifier_token():
    # id = [a-zA-Z][a-zA-Z0-9]*
    dfa = build_direct_dfa("[a-zA-Z][a-zA-Z0-9]*")
    assert dfa.match("x")
    assert dfa.match("x1")
    assert dfa.match("Foo2")
    assert dfa.match("CamelCase123")
    assert not dfa.match("1abc")
    assert not dfa.match("")


def test_number_token():
    # num = [0-9]+
    dfa = build_direct_dfa("[0-9]+")
    assert dfa.match("0")
    assert dfa.match("123")
    assert not dfa.match("")
    assert not dfa.match("12a")


def test_escaped_special_characters():
    dfa = build_direct_dfa("a\\+b")
    assert dfa.match("a+b")
    assert not dfa.match("ab")
    assert not dfa.match("aab")


# ---------------------------------------------------------------------------
# DFA structural sanity checks (useful for the benchmark in Milestone 3)
# ---------------------------------------------------------------------------

def test_dfa_state_count_is_reasonable():
    # (a|b)*abb is the textbook Aho-Ullman example, its minimal DFA has
    # 4 states. The direct method should land on a small state count too,
    # well short of a naive/blown-up construction.
    dfa = build_direct_dfa("(a|b)*abb")
    assert 1 <= len(dfa.states) <= 6


def test_to_dict_is_json_serializable():
    import json

    dfa = build_direct_dfa("[a-zA-Z][a-zA-Z0-9]*")
    # Will raise if anything in here isn't JSON-serializable.
    json.dumps(dfa.to_dict())
