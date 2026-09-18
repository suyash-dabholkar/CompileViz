"""
Parses a context-free grammar written as plain text into a structured
Grammar object that first_follow.py and ll1_table.py operate on.

Expected format, one rule per line:

    E  -> T E'
    E' -> + T E' | ε
    T  -> F T'
    T' -> * F T' | ε
    F  -> ( E ) | id

- '->' or '::=' both work as the production arrow.
- Alternatives on the right-hand side are separated by '|'.
- Symbols within a production are separated by whitespace.
- Epsilon (the empty production) can be written as 'ε', 'eps', or
  'epsilon' (case-insensitive), or simply left blank, e.g. "E' -> ".
- The non-terminal on the left-hand side of the FIRST line is taken as
  the grammar's start symbol.
- Any symbol that never appears as a left-hand side is treated as a
  terminal. This is why every non-terminal needs at least one rule.
- If the same non-terminal appears on multiple lines, its productions
  are merged, so this is equivalent to using '|' on one line.
"""

from __future__ import annotations

from dataclasses import dataclass, field

EPSILON = "\u03b5"  # 'ε', used internally to mark a nullable/empty production
END_MARKER = "$"

_EPSILON_TOKENS = {"\u03b5", "eps", "epsilon"}


class GrammarSyntaxError(ValueError):
    """Raised when the input grammar text cannot be parsed."""


@dataclass
class Grammar:
    start_symbol: str
    productions: dict[str, list[list[str]]]  # non-terminal -> list of productions
    non_terminals: set[str] = field(default_factory=set)
    terminals: set[str] = field(default_factory=set)


def _is_epsilon_token(token: str) -> bool:
    return token.lower() in _EPSILON_TOKENS


def parse_grammar(text: str) -> Grammar:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise GrammarSyntaxError("Empty grammar")

    productions: dict[str, list[list[str]]] = {}
    order: list[str] = []  # first-appearance order, to pick the start symbol

    for line in lines:
        if "->" in line:
            lhs, rhs = line.split("->", 1)
        elif "::=" in line:
            lhs, rhs = line.split("::=", 1)
        else:
            raise GrammarSyntaxError(
                f"Missing '->' (or '::=') in rule: {line!r}"
            )

        lhs = lhs.strip()
        if not lhs:
            raise GrammarSyntaxError(f"Missing left-hand side in rule: {line!r}")
        if "|" in lhs or "->" in lhs:
            raise GrammarSyntaxError(f"Malformed left-hand side in rule: {line!r}")

        if lhs not in productions:
            productions[lhs] = []
            order.append(lhs)

        for alt in rhs.split("|"):
            symbols = [s for s in alt.split() if not _is_epsilon_token(s)]
            productions[lhs].append(symbols)  # [] means an epsilon production

    non_terminals = set(productions.keys())
    terminals: set[str] = set()
    for prods in productions.values():
        for prod in prods:
            for symbol in prod:
                if symbol not in non_terminals:
                    terminals.add(symbol)

    return Grammar(
        start_symbol=order[0],
        productions=productions,
        non_terminals=non_terminals,
        terminals=terminals,
    )
