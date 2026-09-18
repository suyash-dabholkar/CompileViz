"""
DFA minimization via partition refinement (the Myhill-Nerode / Hopcroft
style table-filling approach).

Works on a DFA from EITHER construction method (direct_dfa.py or
subset_construction.py), since both return the same shared DFA type.
That's the point of Milestone 6: it doesn't care how the DFA was built,
only that it IS one.

Algorithm:
    1. Start with two groups: accepting states, and non-accepting states.
       (Two states can only be equivalent if they agree on acceptance.)
    2. Repeatedly split each group: two states in the same group must
       move to the same group when compared, or the group gets split
       into sub-groups by "signature", where a signature is which
       group each symbol's transition leads to (or "no transition" as
       its own consistent category, since a partial DFA can have gaps).
    3. Stop when a full pass produces no new splits, that's the fixed
       point: every remaining group is a set of genuinely
       indistinguishable states.
    4. Each final group becomes one state in the minimized DFA.

The state mapping (which original states merged into which minimized
state) is returned alongside the minimized DFA, along with a trace of
every refinement round, so the frontend can show the partitions
splitting step by step rather than just the final answer.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.automata.dfa import DFA


@dataclass
class MinimizationResult:
    minimized: DFA
    state_mapping: dict[int, int]  # original state index -> minimized state index
    partition_trace: list[list[list[int]]]  # one entry per round, each a list of groups


def minimize_dfa(dfa: DFA) -> MinimizationResult:
    num_states = len(dfa.states)

    accepting = set(dfa.accepting)
    non_accepting = set(range(num_states)) - accepting

    partitions: list[frozenset[int]] = []
    if accepting:
        partitions.append(frozenset(accepting))
    if non_accepting:
        partitions.append(frozenset(non_accepting))

    trace: list[list[list[int]]] = [_snapshot(partitions)]

    changed = True
    while changed:
        changed = False
        state_group = _index_by_state(partitions)

        new_partitions: list[frozenset[int]] = []
        for group in partitions:
            buckets: dict[tuple, set[int]] = {}
            for state in group:
                signature = tuple(
                    state_group.get(dfa.transitions.get((state, symbol)), None)
                    for symbol in dfa.alphabet
                )
                buckets.setdefault(signature, set()).add(state)

            if len(buckets) > 1:
                changed = True
            for bucket in buckets.values():
                new_partitions.append(frozenset(bucket))

        partitions = new_partitions
        trace.append(_snapshot(partitions))

    # Deterministic ordering: the group containing the original start
    # state becomes minimized state 0, the rest ordered by their
    # smallest original state index.
    partitions.sort(key=lambda group: (dfa.start not in group, min(group)))

    state_mapping: dict[int, int] = {}
    for new_index, group in enumerate(partitions):
        for original_state in group:
            state_mapping[original_state] = new_index

    new_transitions: dict[tuple[int, str], int] = {}
    for (state, symbol), target in dfa.transitions.items():
        new_transitions[(state_mapping[state], symbol)] = state_mapping[target]

    minimized = DFA(
        states=[frozenset(group) for group in partitions],
        start=state_mapping[dfa.start],
        accepting={state_mapping[s] for s in dfa.accepting},
        transitions=new_transitions,
        alphabet=dfa.alphabet,
        position_symbol=None,
    )

    return MinimizationResult(
        minimized=minimized,
        state_mapping=state_mapping,
        partition_trace=trace,
    )


def _index_by_state(partitions: list[frozenset[int]]) -> dict[int, int]:
    return {state: idx for idx, group in enumerate(partitions) for state in group}


def _snapshot(partitions: list[frozenset[int]]) -> list[list[int]]:
    return [sorted(group) for group in sorted(partitions, key=lambda g: min(g))]
