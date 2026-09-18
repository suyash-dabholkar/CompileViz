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
) -> LL1Table:
    table: dict[tuple[str, str], list[list[str]]] = {}

    for non_terminal, productions in grammar.productions.items():
        for production in productions:
            production_first = first_of_sequence(production, first)

            terminals_for_this_production = production_first - {EPSILON}
            if EPSILON in production_first:
                terminals_for_this_production |= follow[non_terminal]

            for terminal in terminals_for_this_production:
                key = (non_terminal, terminal)
                table.setdefault(key, []).append(production)

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

    return LL1Table(
        non_terminals=sorted(grammar.non_terminals),
        terminals=sorted(grammar.terminals) + [END_MARKER],
        table=table,
        conflicts=conflicts,
    )
