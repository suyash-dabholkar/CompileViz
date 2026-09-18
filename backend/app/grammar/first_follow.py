"""
FIRST and FOLLOW set computation for a context-free grammar.

Both are computed with the standard fixed-point (worklist) algorithm:
keep sweeping over every production, growing the FIRST/FOLLOW sets
whenever a rule adds something new, and stop once a full sweep makes no
changes. This is deliberately NOT naive recursion into FIRST(X) calling
itself, that would infinite-loop on left-recursive grammars (e.g.
A -> A alpha | beta). The iterative version handles left recursion,
right recursion, or no recursion at all, identically and safely.
"""

from __future__ import annotations

from app.grammar.grammar_parser import EPSILON, END_MARKER, Grammar


def first_of_sequence(sequence: list[str], first: dict[str, set[str]]) -> set[str]:
    """FIRST of a sequence of symbols (a whole production's right-hand
    side, or the tail of one), given each individual symbol's FIRST set.
    Used both while computing FIRST for productions with more than one
    symbol, and again in FOLLOW and LL(1) table construction.
    """
    result: set[str] = set()
    all_nullable = True
    for symbol in sequence:
        symbol_first = first.get(symbol, {symbol})  # terminals are their own FIRST set
        result |= symbol_first - {EPSILON}
        if EPSILON not in symbol_first:
            all_nullable = False
            break
    if all_nullable:
        result.add(EPSILON)
    return result


def compute_first_sets(grammar: Grammar) -> dict[str, set[str]]:
    first: dict[str, set[str]] = {nt: set() for nt in grammar.non_terminals}
    for terminal in grammar.terminals:
        first[terminal] = {terminal}

    changed = True
    while changed:
        changed = False
        for non_terminal, productions in grammar.productions.items():
            for production in productions:
                before = len(first[non_terminal])
                first[non_terminal] |= first_of_sequence(production, first)
                if len(first[non_terminal]) != before:
                    changed = True

    return first


def compute_follow_sets(
    grammar: Grammar, first: dict[str, set[str]]
) -> dict[str, set[str]]:
    follow: dict[str, set[str]] = {nt: set() for nt in grammar.non_terminals}
    follow[grammar.start_symbol].add(END_MARKER)

    changed = True
    while changed:
        changed = False
        for left_hand_side, productions in grammar.productions.items():
            for production in productions:
                for i, symbol in enumerate(production):
                    if symbol not in grammar.non_terminals:
                        continue
                    beta = production[i + 1:]
                    beta_first = first_of_sequence(beta, first)

                    before = len(follow[symbol])
                    follow[symbol] |= beta_first - {EPSILON}
                    if EPSILON in beta_first:
                        follow[symbol] |= follow[left_hand_side]
                    if len(follow[symbol]) != before:
                        changed = True

    return follow
