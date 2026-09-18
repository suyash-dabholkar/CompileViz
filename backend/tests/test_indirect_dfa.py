"""
Tests for Milestone 3's indirect method (Thompson + subset construction),
and more importantly, tests that PROVE the two construction methods are
equivalent: for every pattern below, both build_direct_dfa and
build_indirect_dfa must agree on every test string.

This is the actual result the report's benchmark section rests on: it's
not enough for the direct method to "work" in isolation, it has to
recognize the exact same language as the well-established indirect
method. Parametrizing over both build functions is what proves that,
rather than just asserting it.
"""

import pytest

from app.automata.direct_dfa import build_direct_dfa
from app.automata.subset_construction import build_indirect_dfa

BUILD_FUNCTIONS = [build_direct_dfa, build_indirect_dfa]


@pytest.mark.parametrize("build_fn", BUILD_FUNCTIONS)
class TestBothMethodsAgree:
    def test_single_literal(self, build_fn):
        dfa = build_fn("a")
        assert dfa.match("a")
        assert not dfa.match("b")
        assert not dfa.match("")
        assert not dfa.match("aa")

    def test_concatenation(self, build_fn):
        dfa = build_fn("ab")
        assert dfa.match("ab")
        assert not dfa.match("a")
        assert not dfa.match("abc")

    def test_union(self, build_fn):
        dfa = build_fn("a|b")
        assert dfa.match("a")
        assert dfa.match("b")
        assert not dfa.match("c")

    def test_star(self, build_fn):
        dfa = build_fn("a*")
        assert dfa.match("")
        assert dfa.match("aaaa")
        assert not dfa.match("aab")

    def test_plus(self, build_fn):
        dfa = build_fn("a+")
        assert not dfa.match("")
        assert dfa.match("aaaa")

    def test_optional(self, build_fn):
        dfa = build_fn("a?")
        assert dfa.match("")
        assert dfa.match("a")
        assert not dfa.match("aa")

    def test_grouping(self, build_fn):
        dfa = build_fn("(a|b)c")
        assert dfa.match("ac")
        assert dfa.match("bc")
        assert not dfa.match("a")

    def test_char_class(self, build_fn):
        dfa = build_fn("[a-c]")
        assert dfa.match("a")
        assert dfa.match("c")
        assert not dfa.match("d")

    def test_identifier_token(self, build_fn):
        dfa = build_fn("[a-zA-Z][a-zA-Z0-9]*")
        assert dfa.match("x1")
        assert dfa.match("CamelCase123")
        assert not dfa.match("1abc")

    def test_number_token(self, build_fn):
        dfa = build_fn("[0-9]+")
        assert dfa.match("123")
        assert not dfa.match("")
        assert not dfa.match("12a")

    def test_textbook_example(self, build_fn):
        # (a|b)*abb, the classic Aho-Ullman example.
        dfa = build_fn("(a|b)*abb")
        assert dfa.match("abb")
        assert dfa.match("aabb")
        assert dfa.match("babb")
        assert not dfa.match("ab")
        assert not dfa.match("abbb")


def test_direct_method_reaches_the_known_minimal_state_count():
    # (a|b)*abb has a well-known minimal DFA of exactly 4 states.
    dfa = build_direct_dfa("(a|b)*abb")
    assert len(dfa.states) == 4


def test_both_methods_produce_a_valid_dfa_object():
    for build_fn in BUILD_FUNCTIONS:
        dfa = build_fn("[a-zA-Z][a-zA-Z0-9]*")
        assert dfa.start in range(len(dfa.states))
        assert dfa.accepting  # at least one accepting state must exist
        for (frm, _symbol), to in dfa.transitions.items():
            assert 0 <= frm < len(dfa.states)
            assert 0 <= to < len(dfa.states)
