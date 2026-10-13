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
from app.trace import fmt_set


@dataclass
class MinimizationResult:
    minimized: DFA
    state_mapping: dict[int, int]  # original state index -> minimized state index
    partition_trace: list[list[list[int]]]  # one entry per round, each a list of groups


def minimize_dfa(dfa: DFA, *, tracer=None) -> MinimizationResult:
    """Minimize `dfa` by partition refinement.

    Pass a `tracer` (app.trace.Tracer) to record each round for the
    teaching UI. `partition_trace` below is unchanged either way: it
    predates the tracer, the Result view and the existing endpoint tests
    both rely on it, and it stays the cheap summary while the tracer
    carries the per-group reasoning the summary cannot express.
    """
    num_states = len(dfa.states)

    accepting = set(dfa.accepting)
    non_accepting = set(range(num_states)) - accepting

    partitions: list[frozenset[int]] = []
    if accepting:
        partitions.append(frozenset(accepting))
    if non_accepting:
        partitions.append(frozenset(non_accepting))

    trace: list[list[list[int]]] = [_snapshot(partitions)]

    if tracer:
        tracer.universe = {"kind": "dfa_state", "items": list(range(num_states))}
        tracer.phase("split")
        tracer.step(
            "min.init",
            title=f"Split on acceptance: {fmt_set(accepting)} vs {fmt_set(non_accepting)}",
            explain=(
                f"Two states can only be equivalent if they agree on acceptance, "
                f"since the empty string already tells them apart otherwise. So "
                f"start with exactly that split: the accepting states "
                f"{fmt_set(accepting)} in one group and {fmt_set(non_accepting)} "
                f"in the other. From here groups only ever split further, never "
                f"merge back."
            ),
            result=accepting,
            groups=[sorted(g) for g in partitions],
            highlight={"states": sorted(accepting)},
            ask="Which states are accepting?",
        )

    round_number = 0
    changed = True
    while changed:
        changed = False
        round_number += 1
        state_group = _index_by_state(partitions)

        if tracer:
            tracer.phase(f"round {round_number}")
            tracer.step(
                "min.sweep",
                title=f"Round {round_number}: {len(partitions)} groups to check",
                explain=(
                    f"Sweep over all {len(partitions)} groups. For each one, ask "
                    f"whether its states still belong together: feed every state "
                    f"each input symbol and see which group it lands in. States "
                    f"that disagree are distinguishable and must be separated."
                ),
                result=len(partitions),
                groups=[sorted(g) for g in partitions],
                highlight={"states": sorted(state_group)},
            )

        new_partitions: list[frozenset[int]] = []
        for group in partitions:
            buckets: dict[tuple, set[int]] = {}
            signatures: dict[int, list] = {}
            for state in group:
                signature = tuple(
                    state_group.get(dfa.transitions.get((state, symbol)), None)
                    for symbol in dfa.alphabet
                )
                signatures[state] = list(signature)
                buckets.setdefault(signature, set()).add(state)

            if len(buckets) > 1:
                changed = True

            if tracer:
                _trace_group(tracer, dfa, group, buckets, signatures)

            for bucket in buckets.values():
                new_partitions.append(frozenset(bucket))

        partitions = new_partitions
        trace.append(_snapshot(partitions))

    if tracer:
        tracer.phase("merge")
        tracer.step(
            "min.stable",
            title=f"Fixed point: {len(partitions)} groups, no more splits",
            explain=(
                f"That whole pass split nothing, which is the stopping condition. "
                f"The partition is stable at {len(partitions)} groups, and every "
                f"group now holds states that no input string can tell apart. "
                f"Each one collapses into a single state of the minimized DFA."
            ),
            result=len(partitions),
            groups=[sorted(g) for g in partitions],
        )

    # Deterministic ordering: the group containing the original start
    # state becomes minimized state 0, the rest ordered by their
    # smallest original state index.
    partitions.sort(key=lambda group: (dfa.start not in group, min(group)))

    state_mapping: dict[int, int] = {}
    for new_index, group in enumerate(partitions):
        for original_state in group:
            state_mapping[original_state] = new_index

        if tracer:
            members = sorted(group)
            is_start = dfa.start in group
            accepts = bool(group & set(dfa.accepting))
            notes = []
            if is_start:
                notes.append("it holds the original start state")
            if accepts:
                notes.append("its states are accepting")
            tracer.step(
                "min.merge",
                title=f"{fmt_set(members)} becomes q{new_index}",
                explain=(
                    f"The group {fmt_set(members)} collapses into a single "
                    f"minimized state q{new_index}"
                    + (f", and {' and '.join(notes)}" if notes else "")
                    + ". "
                    + (
                        f"All {len(members)} of them behaved identically on every "
                        f"input, so keeping them apart was wasted work."
                        if len(members) > 1
                        else "It was already distinguishable from everything else, "
                        "so it survives on its own."
                    )
                ),
                result=members,
                minimized_state=new_index,
                is_start=is_start,
                accepting=accepts,
                highlight={"states": members},
            )

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

    if tracer:
        tracer.context.update(
            original=dfa.to_dict(),
            minimized=minimized.to_dict(),
            state_mapping={str(k): v for k, v in state_mapping.items()},
            partition_trace=trace,
        )

    return MinimizationResult(
        minimized=minimized,
        state_mapping=state_mapping,
        partition_trace=trace,
    )


def _trace_group(tracer, dfa: DFA, group, buckets, signatures) -> None:
    """Report one group examined.

    A group that does NOT split gets a step too. Why a group survives is
    half of partition refinement, and a trace that only showed splits
    would teach the algorithm as a sequence of events with no reasoning
    between them.
    """
    members = sorted(group)
    rendered = {
        str(state): {
            symbol: ("-" if target is None else f"G{target}")
            for symbol, target in zip(dfa.alphabet, signature)
        }
        for state, signature in signatures.items()
    }

    if len(buckets) > 1:
        # Which symbols actually did the separating: the positions where
        # the signatures disagree. This is the one fact the partition
        # trace alone can never show, since it only records the before
        # and after.
        signature_list = list(buckets)
        distinguishers = [
            symbol
            for i, symbol in enumerate(dfa.alphabet)
            if len({signature[i] for signature in signature_list}) > 1
        ]
        pieces = " and ".join(fmt_set(sorted(b)) for b in buckets.values())
        tracer.step(
            "min.group",
            title=f"{fmt_set(members)} splits into {pieces}",
            explain=(
                f"The states in {fmt_set(members)} disagree on "
                f"{' and '.join(repr(s) for s in distinguishers)}: feeding that "
                f"symbol sends them into different groups, which means some string "
                f"tells them apart. They cannot be the same state, so the group "
                f"splits into {pieces}."
            ),
            result=True,
            group=members,
            signatures=rendered,
            distinguishers=distinguishers,
            groups=[sorted(b) for b in buckets.values()],
            highlight={"states": members},
            ask=f"Does the group {fmt_set(members)} split this round?",
        )
    else:
        tracer.step(
            "min.group",
            title=f"{fmt_set(members)} survives",
            explain=(
                f"Every state in {fmt_set(members)} lands in the same group on "
                f"every symbol, so nothing here distinguishes them and the group "
                f"stays whole. Surviving a round is not proof of equivalence yet: "
                f"a later split elsewhere can change where these transitions point."
            ),
            result=False,
            group=members,
            signatures=rendered,
            distinguishers=[],
            groups=[members],
            highlight={"states": members},
            ask=f"Does the group {fmt_set(members)} split this round?",
        )


def _index_by_state(partitions: list[frozenset[int]]) -> dict[int, int]:
    return {state: idx for idx, group in enumerate(partitions) for state in group}


def _snapshot(partitions: list[frozenset[int]]) -> list[list[int]]:
    return [sorted(group) for group in sorted(partitions, key=lambda g: min(g))]
