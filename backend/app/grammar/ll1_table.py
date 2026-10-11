"""
LL(1) parsing table construction.

Standard algorithm: for every production A -> alpha,
    - for every terminal a in FIRST(alpha), add alpha to table[A][a]
    - if epsilon is in FIRST(alpha), then for every terminal b in
      FOLLOW(A) (including the end marker $), add alpha to table[A][b]

If any cell ends up with more than one production, the grammar has an
LL(1) conflict there (a FIRST/FIRST or FIRST/FOLLOW clash), and the
table records every colliding production rather than silently keeping
just one, so the frontend can show the conflict, not hide it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.grammar.first_follow import first_of_sequence
from app.grammar.grammar_parser import EPSILON, END_MARKER, Grammar
from app.trace import fmt_set


def _production_str(production: list[str]) -> str:
    return " ".join(production) if production else EPSILON


@dataclass
class LL1Table:
    non_terminals: list[str]
    terminals: list[str]  # includes the end marker $
    table: dict[tuple[str, str], list[list[str]]]
    conflicts: list[dict] = field(default_factory=list)

    @property
    def is_ll1(self) -> bool:
        return not self.conflicts

    def to_dict(self) -> dict:
        cell_map: dict[str, dict[str, list[str]]] = {}
        for (non_terminal, terminal), productions in self.table.items():
            cell_map.setdefault(non_terminal, {})[terminal] = [
                _production_str(p) for p in productions
            ]
        return {
            "non_terminals": self.non_terminals,
            "terminals": self.terminals,
            "is_ll1": self.is_ll1,
            "table": cell_map,
            "conflicts": self.conflicts,
        }


def build_ll1_table(
    grammar: Grammar,
    first: dict[str, set[str]],
    follow: dict[str, set[str]],
    *,
    tracer=None,
) -> LL1Table:
    """Build the parsing table from FIRST and FOLLOW.

    Pass a `tracer` (app.trace.Tracer) to record it being filled one
    production at a time. The unit is the production, not the cell: a
    production writes a whole row of cells in one go, and "which
    terminals does this production claim, and why" is the question the
    table answers.
    """
    table: dict[tuple[str, str], list[list[str]]] = {}

    if tracer:
        tracer.phase("table")

    for non_terminal, productions in grammar.productions.items():
        for production in productions:
            production_first = first_of_sequence(production, first)

            terminals_for_this_production = production_first - {EPSILON}
            nullable = EPSILON in production_first
            if nullable:
                terminals_for_this_production |= follow[non_terminal]

            for terminal in terminals_for_this_production:
                key = (non_terminal, terminal)
                table.setdefault(key, []).append(production)

            if tracer:
                shown = _production_str(production)
                tracer.step(
                    "ll1.production",
                    title=(
                        f"{non_terminal} -> {shown} fills "
                        f"{fmt_set(terminals_for_this_production)}"
                    ),
                    explain=(
                        f"A parser sitting on {non_terminal} picks this "
                        f"production when the next input symbol is one it can "
                        f"start with, so FIRST({shown}) = "
                        f"{fmt_set(production_first - {EPSILON})} goes into row "
                        f"{non_terminal}. "
                        + (
                            f"This production can also derive nothing, and in "
                            f"that case the parser must choose it whenever the "
                            f"lookahead is something that can follow "
                            f"{non_terminal}, so FOLLOW({non_terminal}) = "
                            f"{fmt_set(follow[non_terminal])} is added too."
                            if nullable
                            else "It cannot derive the empty string, so FOLLOW "
                            "plays no part here."
                        )
                    ),
                    result=sorted(terminals_for_this_production),
                    non_terminal=non_terminal,
                    production=shown,
                    production_first=sorted(production_first),
                    nullable=nullable,
                    highlight={"rows": [non_terminal]},
                    ask=f"Which lookaheads select {non_terminal} -> {shown}?",
                )

    conflicts = []
    for (non_terminal, terminal), productions in table.items():
        if len(productions) > 1:
            conflicts.append(
                {
                    "non_terminal": non_terminal,
                    "terminal": terminal,
                    "productions": [_production_str(p) for p in productions],
                }
            )
    conflicts.sort(key=lambda c: (c["non_terminal"], c["terminal"]))

    if tracer:
        for conflict in conflicts:
            tracer.step(
                "ll1.conflict",
                title=(
                    f"Conflict at [{conflict['non_terminal']}, "
                    f"{conflict['terminal']}]"
                ),
                explain=(
                    f"Cell [{conflict['non_terminal']}, {conflict['terminal']}] "
                    f"holds {len(conflict['productions'])} productions: "
                    + "; ".join(conflict["productions"])
                    + f". On seeing '{conflict['terminal']}' a predictive parser "
                    f"has no way to choose between them with one symbol of "
                    f"lookahead, so this grammar is not LL(1). Left factoring or "
                    f"removing left recursion usually fixes it."
                ),
                result=conflict["productions"],
                non_terminal=conflict["non_terminal"],
                terminal=conflict["terminal"],
                highlight={"rows": [conflict["non_terminal"]]},
            )

        tracer.step(
            "ll1.done",
            title=(
                "Grammar is LL(1)"
                if not conflicts
                else f"Grammar is not LL(1): {len(conflicts)} conflict(s)"
            ),
            explain=(
                "Every cell holds at most one production, so one symbol of "
                "lookahead is always enough to pick the next move. A predictive "
                "parser can be driven straight off this table."
                if not conflicts
                else f"{len(conflicts)} cell(s) hold more than one production, so "
                f"no predictive parser can be driven off this table as it stands."
            ),
            result=len(conflicts),
        )

    return LL1Table(
        non_terminals=sorted(grammar.non_terminals),
        terminals=sorted(grammar.terminals) + [END_MARKER],
        table=table,
        conflicts=conflicts,
    )
