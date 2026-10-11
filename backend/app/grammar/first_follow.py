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
from app.trace import fmt_set


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


def _show(production: list[str]) -> str:
    return " ".join(production) if production else EPSILON


def compute_first_sets(grammar: Grammar, *, tracer=None) -> dict[str, set[str]]:
    """FIRST for every non-terminal, by fixed point.

    Pass a `tracer` (app.trace.Tracer) to record the sweeps. Only
    productions that actually grow a set are reported: in a typical run
    most productions add nothing on most passes, and a step per
    no-op would bury the handful that matter. The per-sweep summary
    carries that information instead.
    """
    first: dict[str, set[str]] = {nt: set() for nt in grammar.non_terminals}
    for terminal in grammar.terminals:
        first[terminal] = {terminal}

    if tracer:
        tracer.phase("first")
        tracer.step(
            "first.init",
            title="FIRST starts empty",
            explain=(
                f"FIRST(A) is the set of terminals that can begin a string "
                f"derived from A. Every terminal is its own FIRST, and every "
                f"non-terminal starts empty: "
                f"{', '.join(sorted(grammar.non_terminals))}. The sets only grow "
                f"from here, which is why sweeping until nothing changes "
                f"terminates."
            ),
            result=sorted(grammar.non_terminals),
        )

    sweep = 0
    changed = True
    while changed:
        changed = False
        sweep += 1
        grew = 0

        for non_terminal, productions in grammar.productions.items():
            for production in productions:
                snapshot = set(first[non_terminal])
                addition = first_of_sequence(production, first)
                first[non_terminal] |= addition
                if first[non_terminal] == snapshot:
                    continue

                changed = True
                grew += 1
                if tracer:
                    gained = first[non_terminal] - snapshot
                    tracer.step(
                        "first.production",
                        phase=f"FIRST sweep {sweep}",
                        title=(
                            f"FIRST({non_terminal}) gains {fmt_set(gained)} "
                            f"from {non_terminal} -> {_show(production)}"
                        ),
                        explain=(
                            f"Look at {non_terminal} -> {_show(production)}. "
                            f"Whatever can start the right-hand side can start "
                            f"{non_terminal}, and FIRST of that sequence is "
                            f"{fmt_set(addition)}. That adds {fmt_set(gained)} to "
                            f"FIRST({non_terminal}), which is now "
                            f"{fmt_set(first[non_terminal])}."
                        ),
                        result=gained,
                        non_terminal=non_terminal,
                        production=_show(production),
                        current=sorted(first[non_terminal]),
                        highlight={"rows": [non_terminal]},
                        ask=f"What does this production add to FIRST({non_terminal})?",
                    )

        if tracer:
            tracer.step(
                "first.sweep",
                phase=f"FIRST sweep {sweep}",
                title=(
                    f"Sweep {sweep}: {grew} production(s) added something"
                    if grew
                    else f"Sweep {sweep}: nothing changed, FIRST is final"
                ),
                explain=(
                    f"Pass {sweep} over every production grew {grew} set(s), so "
                    f"another pass is needed: a set that just grew can let an "
                    f"earlier production add more."
                    if grew
                    else f"Pass {sweep} went over every production and added "
                    f"nothing. That is the fixed point, and FIRST is final. "
                    f"Sweeping rather than recursing is what makes this safe on "
                    f"a left-recursive grammar."
                ),
                result=grew,
                sets={nt: sorted(first[nt]) for nt in grammar.non_terminals},
            )

    return first


def compute_follow_sets(
    grammar: Grammar, first: dict[str, set[str]], *, tracer=None
) -> dict[str, set[str]]:
    """FOLLOW for every non-terminal, by the same fixed point.

    Same tracing rule as FIRST: only productions that grow a set are
    reported.
    """
    follow: dict[str, set[str]] = {nt: set() for nt in grammar.non_terminals}
    follow[grammar.start_symbol].add(END_MARKER)

    if tracer:
        tracer.phase("follow")
        tracer.step(
            "follow.init",
            title=f"FOLLOW({grammar.start_symbol}) starts with {END_MARKER}",
            explain=(
                f"FOLLOW(A) is the set of terminals that can appear immediately "
                f"after A in a derivation. Only one thing is known up front: the "
                f"input ends after the start symbol, so {END_MARKER} goes into "
                f"FOLLOW({grammar.start_symbol}). Everything else is discovered "
                f"from where each non-terminal appears on a right-hand side."
            ),
            result=[END_MARKER],
            non_terminal=grammar.start_symbol,
            highlight={"rows": [grammar.start_symbol]},
        )

    sweep = 0
    changed = True
    while changed:
        changed = False
        sweep += 1
        grew = 0

        for left_hand_side, productions in grammar.productions.items():
            for production in productions:
                for i, symbol in enumerate(production):
                    if symbol not in grammar.non_terminals:
                        continue
                    beta = production[i + 1:]
                    beta_first = first_of_sequence(beta, first)

                    snapshot = set(follow[symbol])
                    follow[symbol] |= beta_first - {EPSILON}
                    trailing = EPSILON in beta_first
                    if trailing:
                        follow[symbol] |= follow[left_hand_side]
                    if follow[symbol] == snapshot:
                        continue

                    changed = True
                    grew += 1
                    if tracer:
                        gained = follow[symbol] - snapshot
                        tracer.step(
                            "follow.production",
                            phase=f"FOLLOW sweep {sweep}",
                            title=(
                                f"FOLLOW({symbol}) gains {fmt_set(gained)} from "
                                f"{left_hand_side} -> {_show(production)}"
                            ),
                            explain=(
                                f"In {left_hand_side} -> {_show(production)}, "
                                f"{symbol} is followed by "
                                + (
                                    f"'{_show(beta)}', so everything in "
                                    f"FIRST('{_show(beta)}') = "
                                    f"{fmt_set(beta_first - {EPSILON})} can follow "
                                    f"{symbol}. "
                                    if beta
                                    else f"nothing, so whatever can follow "
                                    f"{left_hand_side} can follow {symbol} too. "
                                )
                                + (
                                    f"That tail can also vanish, so "
                                    f"FOLLOW({left_hand_side}) = "
                                    f"{fmt_set(follow[left_hand_side])} comes "
                                    f"along as well. "
                                    if trailing and beta
                                    else ""
                                )
                                + f"FOLLOW({symbol}) gains {fmt_set(gained)} and is "
                                f"now {fmt_set(follow[symbol])}."
                            ),
                            result=gained,
                            non_terminal=symbol,
                            production=_show(production),
                            current=sorted(follow[symbol]),
                            highlight={"rows": [symbol]},
                            ask=f"What does this production add to FOLLOW({symbol})?",
                        )

        if tracer:
            tracer.step(
                "follow.sweep",
                phase=f"FOLLOW sweep {sweep}",
                title=(
                    f"Sweep {sweep}: {grew} set(s) grew"
                    if grew
                    else f"Sweep {sweep}: nothing changed, FOLLOW is final"
                ),
                explain=(
                    f"Pass {sweep} grew {grew} FOLLOW set(s), so another pass is "
                    f"needed: FOLLOW sets feed into each other, so one growing "
                    f"can let an earlier rule add more."
                    if grew
                    else f"Pass {sweep} added nothing anywhere. FOLLOW has reached "
                    f"its fixed point and the LL(1) table can be built."
                ),
                result=grew,
                sets={nt: sorted(follow[nt]) for nt in grammar.non_terminals},
            )

    return follow
