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

from app.automata.dfa import DFA
from app.automata.regex_parser import (
    Concat,
    Epsilon,
    Leaf,
    Node,
    RegexSyntaxError,
    Star,
    Union,
    assign_node_ids,
    parse_regex,
    to_regex,
    tree_to_dict,
)
from app.trace import fmt_set as _fmt

END_MARKER = "\ue000"  # Unicode Private Use Area, never a real regex symbol
# Previously "#": that collided with any regex whose alphabet legitimately
# includes '#' (e.g. a character class covering '#' through '~', which the
# toy language's STRING token needs in Milestone 7). When a pattern's own
# alphabet contained '#', the algorithm couldn't tell the real end marker
# apart from the user's literal '#', and silently built the wrong DFA
# instead of erroring. The Private Use Area is reserved by the Unicode
# standard for exactly this kind of internal, application-specific use,
# so no real regex should ever need to match it. build_direct_dfa also
# checks for this explicitly below, so if some future pattern ever does
# need the end marker's own character, it fails loudly instead of quietly
# producing a wrong answer.

# Cached per-node attributes, keyed by id(node) since AST nodes aren't hashable
# and two structurally-identical nodes (e.g. after clone()) must stay distinct.
_Attrs = dict[int, tuple[bool, set[int], set[int]]]


# ---------------------------------------------------------------------------
# Teaching-layer helpers
#
# The followpos tables this module builds used to be locals that were
# discarded on return, which meant the frontend only ever saw the finished
# DFA. Everything below exists so a Tracer (app.trace) can narrate the
# construction, and so the annotated syntax tree can be serialized.
# ---------------------------------------------------------------------------


def display_symbol(symbol: str, end_marker: str = None) -> str:
    """Render a symbol for a human. The real end marker is a Unicode
    Private Use Area character (see END_MARKER above) and must never
    reach the UI as a glyph; the textbook writes it as '#'.
    """
    return "#" if symbol == (end_marker or END_MARKER) else symbol


def _ordinal(n: int) -> str:
    """1st, 2nd, 3rd, 4th. Only used in explanation text, but "the 3th
    symbol" on screen during a demo undercuts everything else on it.
    """
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def assign_positions(root: Node, *, tracer=None, node_ids=None) -> dict[int, str]:
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
            if tracer:
                shown = display_symbol(node.symbol)
                tracer.step(
                    "regex.position",
                    phase="positions",
                    title=f"Position {counter} = '{shown}'",
                    explain=(
                        f"Reading the augmented regex left to right, '{shown}' is "
                        f"the {_ordinal(counter)} symbol, so it takes position {counter}. "
                        f"Every leaf needs its own number because this method "
                        f"builds DFA states as sets of positions."
                    ),
                    result=counter,
                    node=(node_ids or {}).get(id(node)),
                    symbol=shown,
                    highlight={
                        "nodes": [(node_ids or {}).get(id(node))],
                        "positions": [counter],
                    },
                )
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


def compute_attrs(
    node: Node, attrs: _Attrs, *, tracer=None, node_ids=None
) -> tuple[bool, set[int], set[int]]:
    """Recursively compute (nullable, firstpos, lastpos) for `node`,
    memoizing results in `attrs` so followpos computation can reuse them
    without recomputing.
    """
    key = id(node)
    if key in attrs:
        return attrs[key]

    sub = dict(tracer=tracer, node_ids=node_ids)
    kind = "leaf"

    if isinstance(node, Leaf):
        result = (False, {node.position}, {node.position})
        why = (
            f"Position {node.position} is the single symbol "
            f"'{display_symbol(node.symbol)}'. One symbol can never match the "
            f"empty string, so it is not nullable; and it is both the first and "
            f"the last thing it matches, so firstpos = lastpos = "
            f"{_fmt({node.position})}."
        )
    elif isinstance(node, Epsilon):
        kind = "epsilon"
        result = (True, set(), set())
        why = (
            "Epsilon matches the empty string, so it is nullable by definition, "
            "and it consumes no symbol at all, so firstpos and lastpos are both "
            "empty."
        )
    elif isinstance(node, Concat):
        kind = "concat"
        if tracer:
            tracer.push()
        left_nullable, left_first, left_last = compute_attrs(node.left, attrs, **sub)
        right_nullable, right_first, right_last = compute_attrs(
            node.right, attrs, **sub
        )
        if tracer:
            tracer.pop()
        nullable = left_nullable and right_nullable
        firstpos = (left_first | right_first) if left_nullable else set(left_first)
        lastpos = (left_last | right_last) if right_nullable else set(right_last)
        result = (nullable, firstpos, lastpos)
        first_rule = (
            "firstpos(left) union firstpos(right), because the left side can vanish"
            if left_nullable
            else "just firstpos(left)"
        )
        last_rule = (
            "lastpos(left) union lastpos(right), because the right side can vanish"
            if right_nullable
            else "just lastpos(right)"
        )
        why = (
            f"Concatenation. The left side is "
            f"{'nullable' if left_nullable else 'not nullable'}, so firstpos is "
            f"{first_rule} = {_fmt(firstpos)}. The right side is "
            f"{'nullable' if right_nullable else 'not nullable'}, so lastpos is "
            f"{last_rule} = {_fmt(lastpos)}. The node itself is nullable only if "
            f"both sides are, which {'holds' if nullable else 'does not hold'} here."
        )
    elif isinstance(node, Union):
        kind = "union"
        if tracer:
            tracer.push()
        left_nullable, left_first, left_last = compute_attrs(node.left, attrs, **sub)
        right_nullable, right_first, right_last = compute_attrs(
            node.right, attrs, **sub
        )
        if tracer:
            tracer.pop()
        result = (
            left_nullable or right_nullable,
            left_first | right_first,
            left_last | right_last,
        )
        why = (
            f"Union. Either branch can start the match, so firstpos is the union "
            f"of both sides = {_fmt(result[1])}; either branch can end it, so "
            f"lastpos is the union too = {_fmt(result[2])}. It is nullable if "
            f"either side is, which {'holds' if result[0] else 'does not hold'} here."
        )
    elif isinstance(node, Star):
        kind = "star"
        if tracer:
            tracer.push()
        _, child_first, child_last = compute_attrs(node.child, attrs, **sub)
        if tracer:
            tracer.pop()
        result = (True, set(child_first), set(child_last))
        why = (
            f"A star is always nullable, because zero repetitions match the empty "
            f"string. Repeating does not change where a match can begin or end, "
            f"so firstpos = {_fmt(result[1])} and lastpos = {_fmt(result[2])} are "
            f"copied straight from the child."
        )
    else:
        raise TypeError(f"Unknown node type: {type(node)!r}")

    attrs[key] = result

    if tracer:
        nullable, firstpos, lastpos = result
        node_id = (node_ids or {}).get(id(node))
        tracer.step(
            f"regex.attrs.{kind}",
            phase="attrs",
            title=f"{type(node).__name__}: firstpos = {_fmt(firstpos)}",
            explain=why,
            result=firstpos,
            node=node_id,
            nullable=nullable,
            firstpos=firstpos,
            lastpos=lastpos,
            highlight={
                "nodes": [node_id],
                "positions": sorted(firstpos | lastpos),
            },
            ask=f"What is firstpos of this {type(node).__name__} node?",
        )

    return result


def compute_followpos(
    node: Node,
    attrs: _Attrs,
    followpos: dict[int, set[int]],
    *,
    tracer=None,
    node_ids=None,
) -> None:
    """Populate `followpos` in place by walking the tree once more, now
    that every node's (nullable, firstpos, lastpos) is known.
    """
    sub = dict(tracer=tracer, node_ids=node_ids)
    if isinstance(node, Concat):
        compute_followpos(node.left, attrs, followpos, **sub)
        compute_followpos(node.right, attrs, followpos, **sub)
        _, right_first, _ = attrs[id(node.right)]
        _, _, left_last = attrs[id(node.left)]
        for position in left_last:
            followpos[position] |= right_first
        if tracer:
            _trace_followpos(
                tracer,
                node_ids,
                node,
                "concat",
                left_last,
                right_first,
                "Rule 1 (concatenation)",
                "anything that can end the left side can be followed by anything "
                "that can start the right side",
            )
    elif isinstance(node, Union):
        compute_followpos(node.left, attrs, followpos, **sub)
        compute_followpos(node.right, attrs, followpos, **sub)
    elif isinstance(node, Star):
        compute_followpos(node.child, attrs, followpos, **sub)
        _, child_first, child_last = attrs[id(node.child)]
        for position in child_last:
            followpos[position] |= child_first
        if tracer:
            _trace_followpos(
                tracer,
                node_ids,
                node,
                "star",
                child_last,
                child_first,
                "Rule 2 (star)",
                "after the last symbol of one repetition the next repetition can "
                "begin, which is the loop-back that makes * work",
            )
    elif isinstance(node, (Leaf, Epsilon)):
        return
    else:
        raise TypeError(f"Unknown node type: {type(node)!r}")


def _trace_followpos(
    tracer, node_ids, node, kind, gaining, gained, rule_name, rule_text
) -> None:
    """Emit one followpos rule application.

    The unit is the rule application, not the position: the textbook has
    exactly two followpos rules, and the question a student actually has
    is "which rule, applied to which node", not "what happened to
    position 4".
    """
    node_id = (node_ids or {}).get(id(node))
    if gaining:
        detail = (
            f"Here that means every position in {_fmt(gaining)} gains {_fmt(gained)}."
        )
    else:
        detail = "Here the left-hand set is empty, so this node adds nothing."
    tracer.step(
        f"regex.followpos.{kind}",
        phase="followpos",
        title=f"{rule_name} at {node_id}",
        explain=f"{rule_name}: {rule_text}. {detail}",
        result=gaining,
        node=node_id,
        gained=gained,
        highlight={
            "nodes": [node_id],
            "positions": sorted(set(gaining) | set(gained)),
        },
        ask=f"Which positions gain a new followpos entry from this {kind} node?",
    )


def _contains_symbol(node: Node, symbol: str) -> bool:
    """True if `symbol` appears as a literal leaf anywhere in the tree.
    Used only to guard against the end-marker collision described above.
    """
    if isinstance(node, Leaf):
        return node.symbol == symbol
    if isinstance(node, Epsilon):
        return False
    if isinstance(node, Concat) or isinstance(node, Union):
        return _contains_symbol(node.left, symbol) or _contains_symbol(
            node.right, symbol
        )
    if isinstance(node, Star):
        return _contains_symbol(node.child, symbol)
    raise TypeError(f"Unknown node type: {type(node)!r}")


def build_direct_dfa(pattern: str, end_marker: str = END_MARKER, *, tracer=None) -> DFA:
    """Build a DFA for `pattern` using the direct (followpos) method.

    Raises RegexSyntaxError (from regex_parser) if `pattern` is invalid,
    or if `pattern`'s own alphabet already contains `end_marker` (which
    would make it impossible to tell the real end marker apart from a
    literal occurrence of the same character, see the END_MARKER note
    above for why this matters).

    Pass a `tracer` (app.trace.Tracer) to have every step of the
    construction recorded for the teaching UI. The DFA returned is
    identical either way; tracing only observes. The tracer also comes
    back carrying `context` (the annotated syntax tree, the position
    table and the finished DFA), so the route does not have to re-run
    any of this to describe it.
    """
    tree = parse_regex(pattern, tracer=tracer)

    if _contains_symbol(tree, end_marker):
        raise RegexSyntaxError(
            f"Pattern's alphabet already contains the end marker {end_marker!r}; "
            "pass a different end_marker to build_direct_dfa."
        )

    augmented = Concat(tree, Leaf(symbol=end_marker))
    node_ids = assign_node_ids(augmented) if tracer else None

    if tracer:
        tracer.step(
            "regex.augment",
            phase="augment",
            title="Augment the regex with an end marker",
            explain=(
                f'The algorithm needs one position that means "the match is '
                f'complete", so the whole pattern is concatenated with a fresh '
                f"symbol written '#': {pattern} becomes ({to_regex(tree)})#. Any "
                f"DFA state containing #'s position will be an accepting state."
            ),
            result=f"({to_regex(tree)})#",
            node=node_ids.get(id(augmented)),
            highlight={"nodes": [node_ids.get(id(augmented))]},
        )

    position_symbol = assign_positions(augmented, tracer=tracer, node_ids=node_ids)

    if tracer:
        # Set now rather than at construction: the positions are what
        # every set-valued quiz answer below is drawn from, and they do
        # not exist until the leaves have been numbered.
        tracer.universe = {"kind": "position", "items": sorted(position_symbol)}

    attrs: _Attrs = {}
    _, root_first, _ = compute_attrs(augmented, attrs, tracer=tracer, node_ids=node_ids)

    followpos: dict[int, set[int]] = {position: set() for position in position_symbol}
    compute_followpos(augmented, attrs, followpos, tracer=tracer, node_ids=node_ids)

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

    if tracer:
        tracer.phase("subset")
        tracer.step(
            "subset.start",
            title=f"Start state q0 = {_fmt(start_state)}",
            explain=(
                f"Every state of this DFA is a SET of positions, not a single "
                f"one. The start state is firstpos of the root, "
                f"{_fmt(start_state)}, which is exactly the set of positions the "
                f"regex could match first. Call it q0."
            ),
            result=start_state,
            state=0,
            highlight={"states": [0], "positions": sorted(start_state)},
        )

    queue: list[frozenset[int]] = [start_state]
    while queue:
        current = queue.pop(0)
        current_idx = state_index[current]

        is_accepting = end_marker_position in current
        if is_accepting:
            accepting.add(current_idx)

        if tracer:
            tracer.step(
                "subset.state",
                title=f"Take q{current_idx} = {_fmt(current)}",
                explain=(
                    f"q{current_idx} = {_fmt(current)}. It "
                    f"{'contains' if is_accepting else 'does not contain'} "
                    f"position {end_marker_position}, the end marker, so it is "
                    f"{'an accepting state' if is_accepting else 'not accepting'}. "
                    f"Now work out where it goes on each input symbol."
                ),
                result=is_accepting,
                state=current_idx,
                positions=sorted(current),
                highlight={"states": [current_idx], "positions": sorted(current)},
                ask=f"Is q{current_idx} an accepting state?",
            )

        for symbol in alphabet:
            target: set[int] = set()
            contributing: set[int] = set()
            for position in current:
                if position_symbol[position] == symbol:
                    contributing.add(position)
                    target |= followpos[position]

            if not target:
                if tracer:
                    tracer.step(
                        "subset.move",
                        title=f"q{current_idx} on '{symbol}': blank",
                        explain=(
                            f"No position in q{current_idx} is labelled '{symbol}', "
                            f"so there is nothing to follow and q{current_idx} has "
                            f"no transition on '{symbol}'. That cell of the "
                            f"transition table stays blank."
                        ),
                        result=[],
                        state=current_idx,
                        symbol=symbol,
                        contributing=[],
                        target_state=None,
                        is_new=False,
                        highlight={"states": [current_idx]},
                    )
                continue

            target_state = frozenset(target)
            is_new = target_state not in state_index
            if is_new:
                state_index[target_state] = len(states)
                states.append(target_state)
                queue.append(target_state)
            target_idx = state_index[target_state]
            transitions[(current_idx, symbol)] = target_idx

            if tracer:
                tracer.step(
                    "subset.move",
                    title=f"q{current_idx} on '{symbol}' goes to q{target_idx}",
                    explain=(
                        f"Of the positions in q{current_idx}, "
                        f"{_fmt(contributing)} "
                        f"{'is' if len(contributing) == 1 else 'are'} labelled "
                        f"'{symbol}'. Taking the union of their followpos gives "
                        f"{_fmt(target)}, which "
                        f"{'is new, so it becomes' if is_new else 'we have already seen as'}"
                        f" q{target_idx}."
                    ),
                    result=target,
                    state=current_idx,
                    symbol=symbol,
                    contributing=sorted(contributing),
                    target_state=target_idx,
                    is_new=is_new,
                    highlight={
                        "states": [current_idx, target_idx],
                        "edges": [f"{current_idx}-{target_idx}"],
                        "positions": sorted(target),
                    },
                    ask=(
                        f"q{current_idx} = {_fmt(current)}. Which positions does it "
                        f"reach on '{symbol}'?"
                    ),
                )

    dfa = DFA(
        states=states,
        start=0,
        accepting=accepting,
        transitions=transitions,
        alphabet=alphabet,
        position_symbol=position_symbol,
    )

    if tracer:
        # The attrs and followpos tables used to die with this call. Hand
        # them to the trace instead, so the UI can show the annotated tree
        # and the followpos table the student is meant to learn to fill in.
        tracer.context.update(
            pattern=pattern,
            tree=tree_to_dict(
                augmented,
                attrs=attrs,
                followpos=followpos,
                node_ids=node_ids,
                end_marker=end_marker,
            ),
            position_symbol={
                str(position): display_symbol(symbol, end_marker)
                for position, symbol in position_symbol.items()
            },
            followpos={str(k): sorted(v) for k, v in followpos.items()},
            end_marker_position=end_marker_position,
            dfa=dfa.to_dict(),
        )

    return dfa
