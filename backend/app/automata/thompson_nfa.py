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

    def __init__(self, tracer=None, node_ids=None) -> None:
        self._next_state = 0
        self.transitions: dict[tuple[int, Optional[str]], set[int]] = {}
        self.tracer = tracer
        self.node_ids = node_ids or {}

    def _fragment(self, node, kind, start, accept, added, edges, explain) -> None:
        """Report one completed fragment.

        The fragment boundaries are the one thing this builder genuinely
        throws away: every rule mutates a single shared transition table,
        so once the NFA is finished there is no record of which subtree
        produced which states. Each rule below knows exactly which states
        and edges it created, so it says so explicitly rather than having
        this inferred from a state-counter range (which would be wrong
        for union and star, whose own states are allocated before their
        children are built).
        """
        if not self.tracer:
            return
        self.tracer.step(
            f"nfa.fragment.{kind}",
            phase="nfa",
            title=f"{type(node).__name__} fragment: q{start} to q{accept}",
            explain=explain,
            result=added,
            node=self.node_ids.get(id(node)),
            start=start,
            accept=accept,
            edges=edges,
            highlight={
                "nodes": [self.node_ids.get(id(node))],
                "states": sorted({start, accept, *added}),
                "edges": edges,
            },
        )

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
            self._fragment(
                node, "leaf", start, accept, [start, accept], [f"{start}-{accept}"],
                f"The literal '{node.symbol}' becomes two brand new states: q{start} "
                f"with a single '{node.symbol}' transition to q{accept}. Every "
                f"Thompson fragment has exactly one start and one accept state, "
                f"which is what lets the rules below glue fragments together "
                f"without ever looking inside them.",
            )
            return start, accept

        if isinstance(node, Epsilon):
            start, accept = self.new_state(), self.new_state()
            self.add_transition(start, EPSILON, accept)
            self._fragment(
                node, "epsilon", start, accept, [start, accept], [f"{start}-{accept}"],
                f"Epsilon becomes two new states q{start} and q{accept} joined by an "
                f"eps-transition, which the automaton may take without consuming any "
                f"input at all.",
            )
            return start, accept

        if isinstance(node, Concat):
            left_start, left_accept = self.build(node.left)
            right_start, right_accept = self.build(node.right)
            self.add_transition(left_accept, EPSILON, right_start)
            self._fragment(
                node, "concat", left_start, right_accept, [],
                [f"{left_accept}-{right_start}"],
                f"Concatenation adds no new states at all. It only wires the left "
                f"fragment's accept state q{left_accept} to the right fragment's "
                f"start state q{right_start} with an eps-transition, so finishing "
                f"the left half immediately begins the right. The combined fragment "
                f"runs from q{left_start} to q{right_accept}.",
            )
            return left_start, right_accept

        if isinstance(node, Union):
            branch_start, branch_accept = self.new_state(), self.new_state()
            left_start, left_accept = self.build(node.left)
            right_start, right_accept = self.build(node.right)
            self.add_transition(branch_start, EPSILON, left_start)
            self.add_transition(branch_start, EPSILON, right_start)
            self.add_transition(left_accept, EPSILON, branch_accept)
            self.add_transition(right_accept, EPSILON, branch_accept)
            self._fragment(
                node, "union", branch_start, branch_accept,
                [branch_start, branch_accept],
                [
                    f"{branch_start}-{left_start}",
                    f"{branch_start}-{right_start}",
                    f"{left_accept}-{branch_accept}",
                    f"{right_accept}-{branch_accept}",
                ],
                f"Union adds two states and four eps-transitions. The new start "
                f"q{branch_start} forks into both alternatives at once, and both "
                f"their accept states join back into the new accept "
                f"q{branch_accept}. Nothing decides which branch to take: that "
                f"unresolved choice is exactly the nondeterminism subset "
                f"construction will have to remove later.",
            )
            return branch_start, branch_accept

        if isinstance(node, Star):
            loop_start, loop_accept = self.new_state(), self.new_state()
            child_start, child_accept = self.build(node.child)
            self.add_transition(loop_start, EPSILON, child_start)
            self.add_transition(loop_start, EPSILON, loop_accept)  # skip the loop
            self.add_transition(child_accept, EPSILON, child_start)  # repeat
            self.add_transition(child_accept, EPSILON, loop_accept)  # exit
            self._fragment(
                node, "star", loop_start, loop_accept, [loop_start, loop_accept],
                [
                    f"{loop_start}-{child_start}",
                    f"{loop_start}-{loop_accept}",
                    f"{child_accept}-{child_start}",
                    f"{child_accept}-{loop_accept}",
                ],
                f"Star adds two states and four eps-transitions, one per thing a "
                f"star can do: q{loop_start} into the child to run it once, "
                f"q{loop_start} straight to q{loop_accept} to skip it entirely, "
                f"q{child_accept} back to q{child_start} to repeat, and "
                f"q{child_accept} out to q{loop_accept} to stop.",
            )
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


def build_thompson_nfa(pattern: str, *, tree=None, tracer=None, node_ids=None) -> NFA:
    """Parse `pattern` and build its NFA via Thompson's construction.

    Raises RegexSyntaxError (from regex_parser) if `pattern` is invalid.

    `tree` lets a caller that has already parsed (build_indirect_dfa,
    which needs the same tree to hand out node ids) reuse its parse
    instead of paying for a second one. `tracer` records the fragment
    boundaries for the teaching UI; the NFA is identical either way.
    """
    if tree is None:
        tree = parse_regex(pattern, tracer=tracer)

    alphabet: set[str] = set()
    _collect_alphabet(tree, alphabet)

    builder = _ThompsonBuilder(tracer=tracer, node_ids=node_ids)
    start, accept = builder.build(tree)

    return NFA(
        start=start,
        accept=accept,
        transitions=builder.transitions,
        num_states=builder._next_state,
        alphabet=sorted(alphabet),
    )
