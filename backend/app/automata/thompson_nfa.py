"""
Thompson's construction: the classic regex -> NFA algorithm.

This is the "indirect" half of the comparison this project is built
around. It builds an NFA with epsilon-transitions from the same AST that
regex_parser.parse_regex produces (the one direct_dfa.py also uses), so
both construction methods start from an identical parse of the pattern,
which is what makes the Milestone 3 benchmark a fair comparison.

Each construction rule below is the standard Thompson fragment: every
subtree becomes a fragment with exactly one start state and one accept
state, and fragments are wired together with epsilon-transitions:

    literal a:      --a--> 
    concatenation:  frag1 --eps--> frag2
    union:          branch into frag1 and frag2, join with eps
    star:           loop back with eps, and an eps bypass to skip it
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.automata.regex_parser import (
    Concat,
    Epsilon,
    Leaf,
    Node,
    Star,
    Union,
    parse_regex,
)

# None is used as the "symbol" for an epsilon-transition, since it can
# never collide with an actual character from the alphabet.
EPSILON = None


@dataclass
class NFA:
    """An NFA with a single start state and a single accept state, which
    Thompson's construction guarantees for every fragment it builds.
    """

    start: int
    accept: int
    transitions: dict[tuple[int, Optional[str]], set[int]]
    num_states: int
    alphabet: list[str]

    def to_dict(self) -> dict:
        """A JSON-friendly view, used by the regex playground API
        (Milestone 4) to animate the construction step by step.
        """
        return {
            "start": self.start,
            "accept": self.accept,
            "num_states": self.num_states,
            "alphabet": self.alphabet,
            "transitions": [
                {
                    "from": frm,
                    "symbol": "\u03b5" if sym is EPSILON else sym,
                    "to": to,
                }
                for (frm, sym), targets in sorted(
                    self.transitions.items(), key=lambda kv: kv[0][0]
                )
                for to in sorted(targets)
            ],
        }


class _ThompsonBuilder:
    """Keeps the running state-counter and transition table while
    recursively building NFA fragments, one per AST node.
    """

    def __init__(self) -> None:
        self._next_state = 0
        self.transitions: dict[tuple[int, Optional[str]], set[int]] = {}

    def new_state(self) -> int:
        state = self._next_state
        self._next_state += 1
        return state

    def add_transition(self, frm: int, symbol: Optional[str], to: int) -> None:
        self.transitions.setdefault((frm, symbol), set()).add(to)

    def build(self, node: Node) -> tuple[int, int]:
        """Returns (start, accept) for the fragment representing `node`."""
        if isinstance(node, Leaf):
            start, accept = self.new_state(), self.new_state()
            self.add_transition(start, node.symbol, accept)
            return start, accept

        if isinstance(node, Epsilon):
            start, accept = self.new_state(), self.new_state()
            self.add_transition(start, EPSILON, accept)
            return start, accept

        if isinstance(node, Concat):
            left_start, left_accept = self.build(node.left)
            right_start, right_accept = self.build(node.right)
            self.add_transition(left_accept, EPSILON, right_start)
            return left_start, right_accept

        if isinstance(node, Union):
            branch_start, branch_accept = self.new_state(), self.new_state()
            left_start, left_accept = self.build(node.left)
            right_start, right_accept = self.build(node.right)
            self.add_transition(branch_start, EPSILON, left_start)
            self.add_transition(branch_start, EPSILON, right_start)
            self.add_transition(left_accept, EPSILON, branch_accept)
            self.add_transition(right_accept, EPSILON, branch_accept)
            return branch_start, branch_accept

        if isinstance(node, Star):
            loop_start, loop_accept = self.new_state(), self.new_state()
            child_start, child_accept = self.build(node.child)
            self.add_transition(loop_start, EPSILON, child_start)
            self.add_transition(loop_start, EPSILON, loop_accept)  # skip the loop
            self.add_transition(child_accept, EPSILON, child_start)  # repeat
            self.add_transition(child_accept, EPSILON, loop_accept)  # exit
            return loop_start, loop_accept

        raise TypeError(f"Unknown node type: {type(node)!r}")


def _collect_alphabet(node: Node, alphabet: set[str]) -> None:
    if isinstance(node, Leaf):
        alphabet.add(node.symbol)
    elif isinstance(node, Epsilon):
        return
    elif isinstance(node, Concat) or isinstance(node, Union):
        _collect_alphabet(node.left, alphabet)
        _collect_alphabet(node.right, alphabet)
    elif isinstance(node, Star):
        _collect_alphabet(node.child, alphabet)
    else:
        raise TypeError(f"Unknown node type: {type(node)!r}")


def build_thompson_nfa(pattern: str) -> NFA:
    """Parse `pattern` and build its NFA via Thompson's construction.

    Raises RegexSyntaxError (from regex_parser) if `pattern` is invalid.
    """
    tree = parse_regex(pattern)

    alphabet: set[str] = set()
    _collect_alphabet(tree, alphabet)

    builder = _ThompsonBuilder()
    start, accept = builder.build(tree)

    return NFA(
        start=start,
        accept=accept,
        transitions=builder.transitions,
        num_states=builder._next_state,
        alphabet=sorted(alphabet),
    )
