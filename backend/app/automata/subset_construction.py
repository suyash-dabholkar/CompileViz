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
from app.automata.regex_parser import assign_node_ids, parse_regex, tree_to_dict
from app.automata.thompson_nfa import EPSILON, NFA, build_thompson_nfa
from app.trace import fmt_set


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


def build_dfa_from_nfa(nfa: NFA, *, tracer=None) -> DFA:
    """Run subset construction on an already-built NFA.

    Pass a `tracer` (app.trace.Tracer) to record each step. Note that
    epsilon_closure and move below are deliberately left uninstrumented:
    everything a step needs is already in hand at the call site, so the
    steps are emitted from here instead, which keeps those two helpers
    (and their existing tests) untouched.
    """
    start_state = epsilon_closure({nfa.start}, nfa.transitions)

    states: list[frozenset[int]] = [start_state]
    state_index: dict[frozenset[int], int] = {start_state: 0}
    transitions: dict[tuple[int, str], int] = {}
    accepting: set[int] = set()

    if tracer:
        tracer.phase("subset")
        tracer.step(
            "subset.closure",
            title=f"Start state q0 = {fmt_set(start_state)}",
            explain=(
                f"One DFA state stands for a whole SET of NFA states: all the "
                f"places the NFA might be at once. Start from the NFA's start "
                f"state q{nfa.start} and follow every eps-transition as far as it "
                f"goes. That eps-closure is {fmt_set(start_state)}, and the whole "
                f"set becomes a single DFA state, q0."
            ),
            result=start_state,
            state=0,
            source=[nfa.start],
            highlight={"states": sorted(start_state)},
        )

    queue: list[frozenset[int]] = [start_state]
    while queue:
        current = queue.pop(0)
        current_idx = state_index[current]

        is_accepting = nfa.accept in current
        if is_accepting:
            accepting.add(current_idx)

        if tracer:
            tracer.step(
                "subset.state",
                title=f"Take q{current_idx} = {fmt_set(current)}",
                explain=(
                    f"q{current_idx} stands for the NFA states "
                    f"{fmt_set(current)}. It "
                    f"{'contains' if is_accepting else 'does not contain'} the "
                    f"NFA's accept state q{nfa.accept}, so it is "
                    f"{'an accepting state' if is_accepting else 'not accepting'}. "
                    f"Now work out where it goes on each input symbol."
                ),
                result=is_accepting,
                state=current_idx,
                nfa_states=sorted(current),
                highlight={"states": sorted(current)},
                ask=f"Is q{current_idx} an accepting state?",
            )

        for symbol in nfa.alphabet:
            reachable = move(current, symbol, nfa.transitions)

            if tracer:
                tracer.step(
                    "subset.move",
                    title=f"move(q{current_idx}, '{symbol}') = {fmt_set(reachable)}",
                    explain=(
                        f"First the move: from the NFA states {fmt_set(current)}, "
                        f"which ones can be reached by actually consuming a "
                        f"'{symbol}'? That gives {fmt_set(reachable)}"
                        + (
                            ". No eps-transitions are followed yet, that is the "
                            "separate step that comes next, and conflating the two "
                            "is the usual way this algorithm goes wrong."
                            if reachable
                            else ", which is empty, so q"
                            f"{current_idx} has no transition on '{symbol}' and "
                            "that cell of the table stays blank."
                        )
                    ),
                    result=reachable,
                    state=current_idx,
                    symbol=symbol,
                    highlight={"states": sorted(reachable) or sorted(current)},
                    ask=(
                        f"q{current_idx} = {fmt_set(current)}. Which NFA states does "
                        f"consuming '{symbol}' reach, before any eps-closure?"
                    )
                    if reachable
                    else None,
                )

            if not reachable:
                continue

            target_state = epsilon_closure(reachable, nfa.transitions)
            is_new = target_state not in state_index
            if is_new:
                state_index[target_state] = len(states)
                states.append(target_state)
                queue.append(target_state)
            target_idx = state_index[target_state]
            transitions[(current_idx, symbol)] = target_idx

            if tracer:
                grew = target_state - reachable
                tracer.step(
                    "subset.closure",
                    title=f"q{current_idx} on '{symbol}' goes to q{target_idx}",
                    explain=(
                        f"Now the eps-closure of {fmt_set(reachable)}: following "
                        f"eps-transitions "
                        + (
                            f"also picks up {fmt_set(grew)}, giving "
                            if grew
                            else "adds nothing here, so it stays "
                        )
                        + f"{fmt_set(target_state)}. That set "
                        + (
                            f"has not been seen before, so it becomes a new DFA "
                            f"state q{target_idx}."
                            if is_new
                            else f"is already q{target_idx}, so no new state is "
                            f"created and the transition just points back at it."
                        )
                    ),
                    result=target_state,
                    state=current_idx,
                    symbol=symbol,
                    source=sorted(reachable),
                    target_state=target_idx,
                    is_new=is_new,
                    highlight={
                        "states": sorted(target_state),
                        "edges": [f"{current_idx}-{target_idx}"],
                    },
                    ask=(
                        f"What is the eps-closure of {fmt_set(reachable)}?"
                        if grew
                        else None
                    ),
                )

    return DFA(
        states=states,
        start=0,
        accepting=accepting,
        transitions=transitions,
        alphabet=nfa.alphabet,
        position_symbol=None,  # only meaningful for the direct method
    )


def build_indirect_dfa(pattern: str, *, tracer=None) -> DFA:
    """The full indirect route in one call: regex -> Thompson NFA ->
    subset construction -> DFA.

    Raises RegexSyntaxError (from regex_parser) if `pattern` is invalid.

    Pass a `tracer` (app.trace.Tracer) to record every step for the
    teaching UI; the DFA returned is identical either way. The tracer
    comes back carrying `context` (the syntax tree, the NFA and the
    finished DFA), so the route does not have to rebuild any of it.
    """
    tree = parse_regex(pattern, tracer=tracer)
    node_ids = assign_node_ids(tree) if tracer else None

    nfa = build_thompson_nfa(pattern, tree=tree, tracer=tracer, node_ids=node_ids)

    if tracer:
        # The NFA's states are what every set-valued answer below is drawn
        # from, and they do not exist until the NFA has been built.
        tracer.universe = {
            "kind": "nfa_state",
            "items": list(range(nfa.num_states)),
        }
        tracer.context.update(
            pattern=pattern,
            tree=tree_to_dict(tree, node_ids=node_ids),
            nfa=nfa.to_dict(),
        )

    dfa = build_dfa_from_nfa(nfa, tracer=tracer)

    if tracer:
        tracer.context["dfa"] = dfa.to_dict()

    return dfa
