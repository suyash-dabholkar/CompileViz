"""
The DFA representation shared by both construction methods.

Both direct_dfa.build_direct_dfa (Milestone 2) and
subset_construction.build_indirect_dfa (Milestone 3) return this same
DFA type. That's deliberate: it's what lets benchmark.py compare them
directly, and it's what lets the lexer (Milestone 7) stay agnostic to
which construction method produced the DFA it's using.

`position_symbol` is the one field specific to the direct method (it
maps a regex position to its symbol, used only for descriptive/debug
purposes during construction). The indirect method has no positions,
so it leaves this as None.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DFA:
    states: list[frozenset[int]]
    start: int
    accepting: set[int]
    transitions: dict[tuple[int, str], int]
    alphabet: list[str]
    position_symbol: Optional[dict[int, str]] = field(default=None, repr=False)

    def match(self, text: str) -> bool:
        """Simulate the DFA on `text`, returning whether it's accepted."""
        current = self.start
        for ch in text:
            key = (current, ch)
            if key not in self.transitions:
                return False
            current = self.transitions[key]
        return current in self.accepting

    def to_dict(self) -> dict:
        """A JSON-friendly view of the DFA, used by the regex playground
        API (Milestone 4) to send diagram data to the frontend.
        """
        return {
            "start": self.start,
            "accepting": sorted(self.accepting),
            "num_states": len(self.states),
            "alphabet": self.alphabet,
            "states": [sorted(s) for s in self.states],
            "transitions": [
                {"from": frm, "symbol": sym, "to": to}
                for (frm, sym), to in sorted(self.transitions.items())
            ],
        }
