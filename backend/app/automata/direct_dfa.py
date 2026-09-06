"""
Direct-method DFA construction (the followpos / Aho-Ullman algorithm).

Given a regular expression, this builds a DFA that recognizes it WITHOUT
ever constructing an intermediate NFA:

    1. Parse the regex into a syntax tree (regex_parser.parse_regex).
    2. Augment it with a unique end-marker symbol: (r)#
    3. Assign every leaf (including the end marker) a unique position.
    4. Compute nullable, firstpos, and lastpos for every node, bottom-up.
    5. Compute followpos(p) for every position p, using the rules:
         - for a concatenation node c1.c2, for every position i in
           lastpos(c1), add firstpos(c2) to followpos(i)
         - for a star node, for every position i in lastpos(child), add
           firstpos(child) to followpos(i)
    6. Build DFA states directly as sets of positions, starting from
       firstpos(root), using followpos to compute transitions.

This module is intentionally standalone (no FastAPI, no I/O) so it can be
unit tested on its own and reused by both the regex playground endpoint
(Milestone 4) and the toy-language lexer (Milestone 7).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.automata.regex_parser import (
    Concat,
    Epsilon,
    Leaf,
    Node,
    Star,
    Union,
    parse_regex,
)

END_MARKER = "#"

# Cached per-node attributes, keyed by id(node) since AST nodes aren't hashable
# and two structurally-identical nodes (e.g. after clone()) must stay distinct.
_Attrs = dict[int, tuple[bool, set[int], set[int]]]


def assign_positions(root: Node) -> dict[int, str]:
    """Walk the tree left to right, giving every Leaf a unique 1-based
    position. Returns a position -> symbol map used throughout the rest
    of the algorithm.
    """
    counter = 0
    position_symbol: dict[int, str] = {}

    def visit(node: Node) -> None:
        nonlocal counter
        if isinstance(node, Leaf):
            counter += 1
            node.position = counter
            position_symbol[counter] = node.symbol
        elif isinstance(node, Epsilon):
            return
        elif isinstance(node, Concat) or isinstance(node, Union):
            visit(node.left)
            visit(node.right)
        elif isinstance(node, Star):
            visit(node.child)
        else:
            raise TypeError(f"Unknown node type: {type(node)!r}")

    visit(root)
    return position_symbol


def compute_attrs(node: Node, attrs: _Attrs) -> tuple[bool, set[int], set[int]]:
    """Recursively compute (nullable, firstpos, lastpos) for `node`,
    memoizing results in `attrs` so followpos computation can reuse them
    without recomputing.
    """
    key = id(node)
    if key in attrs:
        return attrs[key]

    if isinstance(node, Leaf):
        result = (False, {node.position}, {node.position})
    elif isinstance(node, Epsilon):
        result = (True, set(), set())
    elif isinstance(node, Concat):
        left_nullable, left_first, left_last = compute_attrs(node.left, attrs)
        right_nullable, right_first, right_last = compute_attrs(node.right, attrs)
        nullable = left_nullable and right_nullable
        firstpos = (left_first | right_first) if left_nullable else set(left_first)
        lastpos = (left_last | right_last) if right_nullable else set(right_last)
        result = (nullable, firstpos, lastpos)
    elif isinstance(node, Union):
        left_nullable, left_first, left_last = compute_attrs(node.left, attrs)
        right_nullable, right_first, right_last = compute_attrs(node.right, attrs)
        result = (
            left_nullable or right_nullable,
            left_first | right_first,
            left_last | right_last,
        )
    elif isinstance(node, Star):
        _, child_first, child_last = compute_attrs(node.child, attrs)
        result = (True, set(child_first), set(child_last))
    else:
        raise TypeError(f"Unknown node type: {type(node)!r}")

    attrs[key] = result
    return result


def compute_followpos(
    node: Node, attrs: _Attrs, followpos: dict[int, set[int]]
) -> None:
    """Populate `followpos` in place by walking the tree once more, now
    that every node's (nullable, firstpos, lastpos) is known.
    """
    if isinstance(node, Concat):
        compute_followpos(node.left, attrs, followpos)
        compute_followpos(node.right, attrs, followpos)
        _, right_first, _ = attrs[id(node.right)]
        _, _, left_last = attrs[id(node.left)]
        for position in left_last:
            followpos[position] |= right_first
    elif isinstance(node, Union):
        compute_followpos(node.left, attrs, followpos)
        compute_followpos(node.right, attrs, followpos)
    elif isinstance(node, Star):
        compute_followpos(node.child, attrs, followpos)
        _, child_first, child_last = attrs[id(node.child)]
        for position in child_last:
            followpos[position] |= child_first
    elif isinstance(node, (Leaf, Epsilon)):
        return
    else:
        raise TypeError(f"Unknown node type: {type(node)!r}")


@dataclass
class DFA:
    """A DFA built directly from followpos, with states represented as
    sets of regex positions (the textbook representation), but indexed
    by integer for convenient transition lookups.
    """

    states: list[frozenset[int]]
    start: int
    accepting: set[int]
    transitions: dict[tuple[int, str], int]
    alphabet: list[str]
    position_symbol: dict[int, str] = field(repr=False)

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
        API (Milestone 4) to send the diagram data to the frontend.
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


def build_direct_dfa(pattern: str, end_marker: str = END_MARKER) -> DFA:
    """Build a DFA for `pattern` using the direct (followpos) method.

    Raises RegexSyntaxError (from regex_parser) if `pattern` is invalid.
    """
    tree = parse_regex(pattern)
    augmented = Concat(tree, Leaf(symbol=end_marker))

    position_symbol = assign_positions(augmented)

    attrs: _Attrs = {}
    _, root_first, _ = compute_attrs(augmented, attrs)

    followpos: dict[int, set[int]] = {position: set() for position in position_symbol}
    compute_followpos(augmented, attrs, followpos)

    alphabet = sorted(
        {symbol for symbol in position_symbol.values() if symbol != end_marker}
    )
    end_marker_position = next(
        position for position, symbol in position_symbol.items() if symbol == end_marker
    )

    start_state = frozenset(root_first)
    states: list[frozenset[int]] = [start_state]
    state_index: dict[frozenset[int], int] = {start_state: 0}
    transitions: dict[tuple[int, str], int] = {}
    accepting: set[int] = set()

    queue: list[frozenset[int]] = [start_state]
    while queue:
        current = queue.pop(0)
        current_idx = state_index[current]

        if end_marker_position in current:
            accepting.add(current_idx)

        for symbol in alphabet:
            target: set[int] = set()
            for position in current:
                if position_symbol[position] == symbol:
                    target |= followpos[position]
            if not target:
                continue
            target_state = frozenset(target)
            if target_state not in state_index:
                state_index[target_state] = len(states)
                states.append(target_state)
                queue.append(target_state)
            transitions[(current_idx, symbol)] = state_index[target_state]

    return DFA(
        states=states,
        start=0,
        accepting=accepting,
        transitions=transitions,
        alphabet=alphabet,
        position_symbol=position_symbol,
    )
