"""
Regression test for a real bug found while building Milestone 7's
STRING token: direct_dfa.py used the literal character '#' as its
internal end-of-regex marker, which silently broke any pattern whose
own alphabet legitimately included '#' (a character class covering
'#' through '~', as the STRING token's does). The fix moved the
default end marker to a Unicode Private Use Area character, and added
an explicit check that raises a clear error if a pattern's alphabet
ever collides with whatever end marker is in use, instead of quietly
building a wrong DFA.
"""

import pytest

from app.automata.direct_dfa import build_direct_dfa
from app.automata.regex_parser import RegexSyntaxError


def test_character_class_spanning_hash_builds_correctly():
    # The exact pattern shape that exposed the bug: a quoted string
    # whose body is "everything printable except the closing quote",
    # expressed as two ranges that happen to include '#'.
    dfa = build_direct_dfa('"[ -!#-~]*"')
    assert dfa.match('"hello world"')
    assert dfa.match('"contains a # character"')
    assert not dfa.match('"unterminated')
    assert not dfa.match("no quotes at all")


def test_literal_hash_as_an_ordinary_character_matches():
    dfa = build_direct_dfa("a#b")
    assert dfa.match("a#b")
    assert not dfa.match("ab")


def test_end_marker_collision_raises_a_clear_error_instead_of_a_wrong_dfa():
    # If a pattern's own alphabet contains the exact character being used
    # as the end marker, that's now a loud error, not a silent miscount.
    with pytest.raises(RegexSyntaxError):
        build_direct_dfa("a", end_marker="a")
