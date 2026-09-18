"""
Subset construction: converts an NFA (with epsilon-transitions) into an
equivalent DFA.

This is the second half of the "indirect method": regex -> Thompson NFA
(thompson_nfa.py) -> DFA (this module), as opposed to the direct method
in direct_dfa.py, which builds the DFA straight from the regex with no
NFA step at all. Both paths end up producing the same shared DFA type
(app.automata.dfa.DFA), which is what lets benchmark.py compare them
directly and lets the lexer (Milestone 7) use either one interchangeably.

Algorithm, textbook subset construction:
    1. The DFA start state is the epsilon-closure of the NFA start state.
    2. For each unmarked DFA state S and each symbol c in the alphabet,
       compute move(S, c) then take its epsilon-closure. That's the
       transition on c from S.
    3. Repeat until no new states are discovered.
    4. A DFA state is accepting if it contains the NFA's accept state.
"""

from __future__ import annotations

from app.automata.dfa import DFA
from app.automata.thompson_nfa import EPSILON, NFA, build_thompson_nfa


def epsilon_closure(states: set[int], transitions: dict) -> frozenset[int]:
    """All states reachable from `states` using only epsilon-transitions,
    including `states` themselves.
    """
    closure = set(states)
    stack = list(states)
    while stack:
        state = stack.pop()
        for target in transitions.get((state, EPSILON), ()):
            if target not in closure:
                closure.add(target)
                stack.append(target)
    return frozenset(closure)


def move(states: set[int], symbol: str, transitions: dict) -> set[int]:
    """All states reachable from `states` on a single `symbol` transition
    (no epsilon-closure applied yet, the caller does that).
    """
    result: set[int] = set()
    for state in states:
        result |= transitions.get((state, symbol), set())
    return result


def build_dfa_from_nfa(nfa: NFA) -> DFA:
    """Run subset construction on an already-built NFA."""
    start_state = epsilon_closure({nfa.start}, nfa.transitions)

    states: list[frozenset[int]] = [start_state]
    state_index: dict[frozenset[int], int] = {start_state: 0}
    transitions: dict[tuple[int, str], int] = {}
    accepting: set[int] = set()

    queue: list[frozenset[int]] = [start_state]
    while queue:
        current = queue.pop(0)
        current_idx = state_index[current]

        if nfa.accept in current:
            accepting.add(current_idx)

        for symbol in nfa.alphabet:
            reachable = move(current, symbol, nfa.transitions)
            if not reachable:
                continue
            target_state = epsilon_closure(reachable, nfa.transitions)
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
        alphabet=nfa.alphabet,
        position_symbol=None,  # only meaningful for the direct method
    )


def build_indirect_dfa(pattern: str) -> DFA:
    """The full indirect route in one call: regex -> Thompson NFA ->
    subset construction -> DFA.

    Raises RegexSyntaxError (from regex_parser) if `pattern` is invalid.
    """
    nfa = build_thompson_nfa(pattern)
    return build_dfa_from_nfa(nfa)
