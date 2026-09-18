"""
The lexer: turns toy-language source text into a list of Tokens.

Built directly on the Milestone 2 direct-method DFA engine, one DFA per
token type (see token_specs.py). At each position in the source, every
token type's DFA is simulated to find the longest prefix it accepts
(_longest_accepted_prefix), and the overall longest match wins, the
standard "maximal munch" rule every real lexer uses, e.g. so "123"
tokenizes as one INT rather than three separate digits, and "==" wins
over two separate "=" tokens.

Errors don't stop the lexer. An unrecognized character is recorded as
a LexError and skipped, and tokenizing continues, so a single pass can
report every bad character in a file at once, useful for the inline
error highlighting the dashboard will do in a later milestone, and
just generally more useful than stopping at the first typo.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.automata.dfa import DFA
from app.automata.direct_dfa import build_direct_dfa
from app.compiler.token_specs import KEYWORDS, SKIP_TYPES, TOKEN_SPECS


@dataclass
class Token:
    type: str
    value: str
    line: int
    column: int

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "value": self.value,
            "line": self.line,
            "column": self.column,
        }


@dataclass
class LexError:
    message: str
    line: int
    column: int

    def to_dict(self) -> dict:
        return {"message": self.message, "line": self.line, "column": self.column}


@dataclass
class LexResult:
    tokens: list[Token]
    errors: list[LexError]

    def to_dict(self) -> dict:
        return {
            "tokens": [t.to_dict() for t in self.tokens],
            "errors": [e.to_dict() for e in self.errors],
        }


def _build_token_dfas() -> list[tuple[str, DFA]]:
    """Builds one DFA per token spec, once, at import time. Kept as a
    list (not a dict) so TOKEN_SPECS' order is preserved exactly, that
    order is what breaks ties between equal-length matches.
    """
    return [(name, build_direct_dfa(pattern)) for name, pattern in TOKEN_SPECS]


_TOKEN_DFAS = _build_token_dfas()


def _longest_accepted_prefix(dfa: DFA, text: str, start: int) -> int | None:
    """The length of the longest prefix of text[start:] that `dfa`
    accepts, or None if no non-empty prefix is accepted.
    """
    state = dfa.start
    best_length: int | None = None
    if state in dfa.accepting:
        best_length = 0

    i = start
    while i < len(text):
        key = (state, text[i])
        if key not in dfa.transitions:
            break
        state = dfa.transitions[key]
        i += 1
        if state in dfa.accepting:
            best_length = i - start

    # A zero-length "match" is filtered out rather than returned: none
    # of this project's token patterns actually accept the empty
    # string, but if one ever did, returning 0 here would let the
    # tokenize() loop below pick it as a token with no characters
    # consumed, looping forever at the same position.
    return best_length if best_length != 0 else None


def tokenize(source: str) -> LexResult:
    tokens: list[Token] = []
    errors: list[LexError] = []

    pos = 0
    line = 1
    column = 1

    while pos < len(source):
        best_length = -1
        best_type: str | None = None

        for type_name, dfa in _TOKEN_DFAS:
            length = _longest_accepted_prefix(dfa, source, pos)
            if length is not None and length > best_length:
                best_length = length
                best_type = type_name
            # A strictly-greater comparison means an earlier spec in
            # TOKEN_SPECS keeps its match on a tie, that's the whole
            # tie-breaking rule.

        if best_type is None:
            errors.append(
                LexError(
                    f"Unexpected character {source[pos]!r}", line, column
                )
            )
            if source[pos] == "\n":
                line += 1
                column = 1
            else:
                column += 1
            pos += 1
            continue

        lexeme = source[pos : pos + best_length]
        token_type = best_type
        if token_type == "IDENTIFIER" and lexeme in KEYWORDS:
            token_type = "KEYWORD"

        if token_type not in SKIP_TYPES:
            tokens.append(Token(type=token_type, value=lexeme, line=line, column=column))

        for ch in lexeme:
            if ch == "\n":
                line += 1
                column = 1
            else:
                column += 1
        pos += best_length

    return LexResult(tokens=tokens, errors=errors)
