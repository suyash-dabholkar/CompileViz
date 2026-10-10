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
_DFA_BY_NAME = dict(_TOKEN_DFAS)


def _longest_accepted_prefix(
    dfa: DFA, text: str, start: int, *, tracer=None, token_type: str = None
) -> int | None:
    """The length of the longest prefix of text[start:] that `dfa`
    accepts, or None if no non-empty prefix is accepted.

    With a `tracer`, each character of the walk is reported. tokenize()
    below only ever traces the winning spec's walk, never all of them:
    every position would otherwise emit one step per token pattern, and
    the signal would be buried.
    """
    state = dfa.start
    best_length: int | None = None
    if state in dfa.accepting:
        best_length = 0

    i = start
    while i < len(text):
        key = (state, text[i])
        if key not in dfa.transitions:
            if tracer:
                tracer.step(
                    "lex.scan",
                    title=f"{text[i]!r}: no transition, stop",
                    explain=(
                        f"From state {state} there is no transition on "
                        f"{text[i]!r}, so the {token_type} pattern cannot consume "
                        f"any more. The match ends at "
                        f"{'length ' + str(best_length) if best_length else 'nothing'}."
                    ),
                    result=best_length or 0,
                    char=text[i],
                    offset=i,
                    state_before=state,
                    state_after=None,
                    accepting=False,
                    best_length=best_length or 0,
                    highlight={"chars": [i]},
                )
            break
        previous = state
        state = dfa.transitions[key]
        i += 1
        if state in dfa.accepting:
            best_length = i - start
        if tracer:
            accepting = state in dfa.accepting
            tracer.step(
                "lex.scan",
                title=f"{text[i - 1]!r}: state {previous} to {state}",
                explain=(
                    f"Reading {text[i - 1]!r} moves the {token_type} DFA from "
                    f"state {previous} to state {state}. "
                    + (
                        f"State {state} is accepting, so the longest match so far "
                        f"is {best_length} character(s) - but the scan keeps going, "
                        f"because a longer match may still be ahead."
                        if accepting
                        else f"State {state} is not accepting, so this is not yet "
                        f"a valid token; the longest match so far stays at "
                        f"{best_length or 0}."
                    )
                ),
                result=best_length or 0,
                char=text[i - 1],
                offset=i - 1,
                state_before=previous,
                state_after=state,
                accepting=accepting,
                best_length=best_length or 0,
                highlight={"chars": [i - 1]},
            )

    # A zero-length "match" is filtered out rather than returned: none
    # of this project's token patterns actually accept the empty
    # string, but if one ever did, returning 0 here would let the
    # tokenize() loop below pick it as a token with no characters
    # consumed, looping forever at the same position.
    return best_length if best_length != 0 else None


def tokenize(source: str, *, tracer=None) -> LexResult:
    """Scan `source` into tokens by maximal munch.

    Pass a `tracer` (app.trace.Tracer) to record the scan: which
    patterns competed at each position, how the winner's DFA consumed
    the characters one at a time, and what token came out.
    """
    tokens: list[Token] = []
    errors: list[LexError] = []

    pos = 0
    line = 1
    column = 1

    if tracer:
        tracer.phase("lex")
        tracer.context["source"] = source

    while pos < len(source):
        best_length = -1
        best_type: str | None = None
        candidates: list[dict] = []

        for type_name, dfa in _TOKEN_DFAS:
            length = _longest_accepted_prefix(dfa, source, pos)
            if length is not None and length > best_length:
                best_length = length
                best_type = type_name
            # A strictly-greater comparison means an earlier spec in
            # TOKEN_SPECS keeps its match on a tie, that's the whole
            # tie-breaking rule.
            if tracer and length is not None:
                candidates.append({"type": type_name, "length": length})

        if tracer and best_type is not None:
            longest = max(c["length"] for c in candidates)
            tied = [c["type"] for c in candidates if c["length"] == longest]
            tracer.step(
                "lex.compete",
                title=f"At offset {pos}: {best_type} wins with {best_length} char(s)",
                explain=(
                    f"Every token pattern gets a try at offset {pos}. "
                    f"{len(candidates)} of them match here: "
                    + ", ".join(f"{c['type']} ({c['length']})" for c in candidates[:6])
                    + ("..." if len(candidates) > 6 else "")
                    + f". Maximal munch takes the longest, so {best_type} wins with "
                    f"{best_length} character(s)."
                    + (
                        f" {len(tied)} patterns tied at that length, and the tie "
                        f"goes to whichever is declared first in TOKEN_SPECS."
                        if len(tied) > 1
                        else ""
                    )
                ),
                result=best_type,
                offset=pos,
                line=line,
                column=column,
                candidates=candidates,
                length=best_length,
                highlight={"chars": list(range(pos, pos + best_length))},
                ask=f"Which pattern wins at offset {pos}?",
                choices=sorted({c["type"] for c in candidates}),
            )
            # Replay just the winner, character by character, so the
            # maximal-munch walk is visible without 30-odd parallel DFAs
            # drowning it out.
            _longest_accepted_prefix(
                _DFA_BY_NAME[best_type], source, pos,
                tracer=tracer, token_type=best_type,
            )

        if best_type is None:
            if tracer:
                tracer.step(
                    "lex.error",
                    title=f"No pattern matches {source[pos]!r}",
                    explain=(
                        f"Not one token pattern accepts {source[pos]!r} at offset "
                        f"{pos}, so this character cannot begin any token. The "
                        f"lexer reports it and skips one character rather than "
                        f"giving up, so later errors are still found."
                    ),
                    result=source[pos],
                    offset=pos,
                    line=line,
                    column=column,
                    highlight={"chars": [pos], "lines": [line]},
                )
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
        reclassified = token_type == "IDENTIFIER" and lexeme in KEYWORDS
        if reclassified:
            token_type = "KEYWORD"

        skipped = token_type in SKIP_TYPES
        if not skipped:
            tokens.append(Token(type=token_type, value=lexeme, line=line, column=column))

        if tracer:
            tracer.step(
                "lex.token",
                title=(
                    f"{token_type} {lexeme!r}"
                    + (" (skipped)" if skipped else "")
                ),
                explain=(
                    (
                        f"{lexeme!r} matched the IDENTIFIER pattern, but it is in "
                        f"the keyword list, so it is reclassified as a KEYWORD. "
                        f"Keywords are not given their own patterns: that would "
                        f"mean one DFA per keyword, all competing with IDENTIFIER "
                        f"on every single word."
                        if reclassified
                        else f"The {token_type} token {lexeme!r} is complete, at "
                        f"line {line}, column {column}."
                    )
                    + (
                        f" {token_type} is trivia, so it is scanned but never "
                        f"handed to the parser."
                        if skipped
                        else ""
                    )
                ),
                result=lexeme,
                token_type=token_type,
                matched_as=best_type,
                reclassified=reclassified,
                skipped=skipped,
                line=line,
                column=column,
                offset=pos,
                highlight={
                    "chars": list(range(pos, pos + best_length)),
                    "lines": [line],
                },
            )

        for ch in lexeme:
            if ch == "\n":
                line += 1
                column = 1
            else:
                column += 1
        pos += best_length

    return LexResult(tokens=tokens, errors=errors)
