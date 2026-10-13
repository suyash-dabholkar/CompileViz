"""
Tests for the step-trace teaching layer.

Two things are being protected here. First, that tracing only ever
observes: the DFA returned with a tracer attached must be identical to
the one returned without, because the trace is a teaching aid and the
tool must not have two behaviours. Second, that the trace agrees with
the textbook, since a visualization that confidently teaches the wrong
followpos table is worse than no visualization at all.
"""

from __future__ import annotations

import pytest
from app.automata.direct_dfa import END_MARKER, build_direct_dfa
from app.automata.minimization import minimize_dfa
from app.automata.regex_parser import (
    assign_node_ids,
    parse_regex,
    to_regex,
    tree_to_dict,
)
from app.automata.subset_construction import build_indirect_dfa
from app.main import app
from app.trace import HIGHLIGHT_KEYS, SCHEMA, Tracer
from fastapi.testclient import TestClient

client = TestClient(app)

# The patterns the frontend ships as presets, so whatever a professor
# clicks during a demo is covered here.
PRESET_PATTERNS = [
    "(a|b)*abb",
    "[a-zA-Z][a-zA-Z0-9]*",
    "[0-9]+",
    "[0-9]+\\.[0-9]+",
    "a(b|c)*d",
    "colou?r",
]


METHODS = {"direct": build_direct_dfa, "indirect": build_indirect_dfa}


def minimize_trace_for(pattern: str, method: str = "indirect") -> Tracer:
    dfa = METHODS[method](pattern)
    tracer = Tracer(tool="dfa.minimize", title=f"Refinement for {pattern}")
    minimize_dfa(dfa, tracer=tracer)
    return tracer


def trace_for(pattern: str, method: str = "direct") -> Tracer:
    tracer = Tracer(tool=f"regex.{method}", title=f"{method} method for {pattern}")
    METHODS[method](pattern, tracer=tracer)
    return tracer


# ---------------------------------------------------------------------------
# Tracing must not change the result
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("method", ["direct", "indirect"])
@pytest.mark.parametrize("pattern", PRESET_PATTERNS)
def test_tracing_does_not_change_the_dfa(pattern, method):
    build = METHODS[method]
    with_trace = build(pattern, tracer=Tracer(tool=f"regex.{method}"))
    without_trace = build(pattern)
    assert with_trace.to_dict() == without_trace.to_dict()


@pytest.mark.parametrize("method", ["direct", "indirect"])
@pytest.mark.parametrize("pattern", PRESET_PATTERNS)
def test_traced_dfa_still_matches_the_same_strings(pattern, method):
    """A DFA whose construction was observed must still recognize the
    same language, not just serialize to the same dict.
    """
    build = METHODS[method]
    traced = build(pattern, tracer=Tracer(tool=f"regex.{method}"))
    plain = build(pattern)
    for text in ["", "a", "ab", "abb", "aabb", "x", "0", "01", "colour", "color"]:
        assert traced.match(text) == plain.match(text)


# ---------------------------------------------------------------------------
# Schema invariants the frontend relies on
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("method", ["direct", "indirect"])
@pytest.mark.parametrize("pattern", PRESET_PATTERNS)
def test_every_step_satisfies_the_schema(pattern, method):
    steps = trace_for(pattern, method).steps
    assert steps, "a construction with no steps teaches nothing"

    for index, step in enumerate(steps):
        where = f"{pattern} step {index} ({step.get('kind')})"

        # Contiguous indices: the stepper scrubs by array position and
        # labels by `i`, so a gap would mislabel every later step.
        assert step["i"] == index, where

        assert step["kind"], where
        assert step["title"], where
        assert step["phase"], where
        assert isinstance(step["depth"], int) and step["depth"] >= 0, where

        # The explanation is the whole point of the layer, not a
        # nice-to-have: a step without one is a step the UI cannot teach
        # from. 20 chars is enough to catch a placeholder.
        assert len(step["explain"]) >= 20, where

        # Every quiz and every "what changed" highlight derives from it.
        assert "result" in step["data"], where

        # Fixed-key bag, so no renderer needs an existence check.
        assert set(step["highlight"]) == set(HIGHLIGHT_KEYS), where
        for key in HIGHLIGHT_KEYS:
            assert isinstance(step["highlight"][key], list), f"{where}/{key}"


@pytest.mark.parametrize("method", ["direct", "indirect"])
@pytest.mark.parametrize("pattern", PRESET_PATTERNS)
def test_quizzes_are_answerable(pattern, method):
    """A quiz whose answer is not in the universe it offers cannot be
    answered by picking from that universe.
    """
    tracer = trace_for(pattern, method)
    quizzed = 0
    for step in tracer.steps:
        quiz = step["quiz"]
        if quiz is None:
            continue
        quizzed += 1
        assert quiz["question"], step["kind"]
        assert quiz["kind"] in {"set", "number", "choice"}, step["kind"]
        if quiz["kind"] == "set":
            assert quiz["universe"], step["kind"]
            assert set(quiz["answer"]) <= set(quiz["universe"]), step["kind"]
        if quiz["kind"] == "choice":
            assert quiz["answer"] in quiz["choices"], step["kind"]
    assert quizzed > 0, "nothing to self-test on"


@pytest.mark.parametrize(
    "pattern,expected",
    [
        # No +, ? or [] to rewrite, so there is no parse phase at all.
        ("(a|b)*abb", ["augment", "positions", "attrs", "followpos", "subset"]),
        # Desugaring happens during parsing, before anything else.
        ("a+b?", ["parse", "augment", "positions", "attrs", "followpos", "subset"]),
    ],
)
def test_phases_appear_in_algorithm_order(pattern, expected):
    """The phase ribbon groups contiguous runs of the same phase, so a
    phase that reappears after another has started would render as two
    separate segments and read as if the algorithm backtracked.
    """
    phases = [step["phase"] for step in trace_for(pattern).steps]
    runs = [p for i, p in enumerate(phases) if i == 0 or phases[i - 1] != p]
    assert runs == expected
    assert len(runs) == len(set(runs)), "a phase restarted after another began"


def test_limit_truncates_instead_of_exploding():
    tracer = Tracer(tool="regex.direct", limit=5)
    build_direct_dfa("(a|b)*abb", tracer=tracer)
    assert len(tracer.steps) == 5
    assert tracer.truncated is True
    assert tracer.to_dict()["truncated"] is True


def test_choice_quiz_without_choices_is_rejected():
    """A string-valued answer with no choices would render as an
    unanswerable question, so it fails at emit time rather than in the UI.
    """
    tracer = Tracer(tool="t")
    with pytest.raises(ValueError):
        tracer.step("k", title="t", explain="x" * 25, result="abc", ask="which?")


# ---------------------------------------------------------------------------
# The trace must agree with the textbook
# ---------------------------------------------------------------------------


def test_followpos_matches_the_textbook_for_the_classic_example():
    """Aho/Ullman's worked example for (a|b)*abb. If the trace and the
    textbook disagree, the tool is teaching something wrong.
    """
    context = trace_for("(a|b)*abb").context
    assert context["position_symbol"] == {
        "1": "a",
        "2": "b",
        "3": "a",
        "4": "b",
        "5": "b",
        "6": "#",
    }
    assert context["followpos"] == {
        "1": [1, 2, 3],
        "2": [1, 2, 3],
        "3": [4],
        "4": [5],
        "5": [6],
        "6": [],
    }


def test_start_state_is_firstpos_of_the_root():
    tracer = trace_for("(a|b)*abb")
    start = next(s for s in tracer.steps if s["kind"] == "subset.start")
    root = next(
        s
        for s in tracer.steps
        if s["kind"].startswith("regex.attrs") and s["depth"] == 0
    )
    assert start["data"]["result"] == root["data"]["firstpos"] == [1, 2, 3]
    assert start["data"]["result"] == tracer.context["dfa"]["states"][0]


def test_accepting_states_are_exactly_those_holding_the_end_marker():
    tracer = trace_for("(a|b)*abb")
    end_position = tracer.context["end_marker_position"]
    from_steps = {
        s["data"]["state"]
        for s in tracer.steps
        if s["kind"] == "subset.state" and s["data"]["result"] is True
    }
    dfa = tracer.context["dfa"]
    assert from_steps == set(dfa["accepting"])
    assert all(end_position in dfa["states"][q] for q in from_steps)


def test_subset_moves_account_for_every_transition():
    """Every edge in the finished DFA must have been explained by a step,
    and no step may claim an edge the DFA does not have.
    """
    tracer = trace_for("a(b|c)*d")
    dfa = tracer.context["dfa"]
    explained = {
        (s["data"]["state"], s["data"]["symbol"], s["data"]["target_state"])
        for s in tracer.steps
        if s["kind"] == "subset.move" and s["data"]["target_state"] is not None
    }
    actual = {(t["from"], t["symbol"], t["to"]) for t in dfa["transitions"]}
    assert explained == actual


def test_blank_cells_are_explained_too():
    """The blanks in the transition table are part of the lesson, so a
    (state, symbol) pair with no target still gets a step.
    """
    tracer = trace_for("a(b|c)*d")
    dfa = tracer.context["dfa"]
    blanks = {
        (s["data"]["state"], s["data"]["symbol"])
        for s in tracer.steps
        if s["kind"] == "subset.move" and s["data"]["target_state"] is None
    }
    filled = {(t["from"], t["symbol"]) for t in dfa["transitions"]}
    expected = {
        (q, symbol)
        for q in range(dfa["num_states"])
        for symbol in dfa["alphabet"]
        if (q, symbol) not in filled
    }
    assert blanks == expected


def test_desugaring_is_reported():
    """`a+`, `a?` and `[a-c]` are rewritten away during parsing and leave
    no trace in the final tree, which is exactly why students ask where
    their `+` went.
    """
    kinds = lambda p: [
        s["data"]["result"] for s in trace_for(p).steps if s["kind"] == "regex.desugar"
    ]
    assert kinds("a+") == ["aa*"]
    assert kinds("a?") == ["a|ε"]
    assert kinds("[a-c]") == ["a|b|c"]
    assert kinds("(a|b)*abb") == []


def test_end_marker_is_never_shown_as_its_real_character():
    """END_MARKER is a Unicode Private Use Area character; leaking it to
    the UI renders as a blank box or a tofu glyph.
    """
    tracer = trace_for("(a|b)*abb")
    blob = repr(tracer.to_dict())
    assert END_MARKER not in blob
    assert "#" in tracer.context["position_symbol"].values()


# ---------------------------------------------------------------------------
# Tree serialization
# ---------------------------------------------------------------------------


def test_tree_to_dict_without_attrs_has_null_annotations():
    tree = tree_to_dict(parse_regex("ab"))
    assert tree["kind"] == "Concat"
    assert tree["nullable"] is None
    assert tree["firstpos"] is None
    assert tree["left"]["symbol"] == "a"
    assert tree["right"]["symbol"] == "b"


def test_tree_node_ids_are_unique_and_preorder():
    tree = parse_regex("(a|b)*abb")
    ids = assign_node_ids(tree)
    assert len(set(ids.values())) == len(ids)
    assert ids[id(tree)] == "n1", "the root is visited first"
    serialized = tree_to_dict(tree, node_ids=ids)
    assert serialized["id"] == "n1"


def test_tree_child_keys_are_the_dataclass_field_names():
    """AstTreeView labels children by their key, so these names are a
    contract with the frontend, not an implementation detail.
    """
    assert set(tree_to_dict(parse_regex("a|b"))) >= {"left", "right"}
    assert "child" in tree_to_dict(parse_regex("a*"))


def test_annotated_tree_carries_followpos_on_leaves_only():
    tracer = trace_for("(a|b)*abb")
    tree = tracer.context["tree"]

    def walk(node):
        yield node
        for key in ("left", "right", "child"):
            if key in node:
                yield from walk(node[key])

    for node in walk(tree):
        if node["kind"] == "Leaf":
            assert node["position"] is not None, node
            assert node["followpos"] is not None, node
        else:
            assert node["followpos"] is None, node
        if node["kind"] not in {"Epsilon"}:
            assert node["firstpos"] is not None, node


def test_to_regex_round_trips_the_presets():
    """The renderer is what the desugaring steps quote, so it has to be
    faithful: re-parsing its output must give the same language.
    """
    for pattern in ["(a|b)*abb", "a(b|c)*d", "a|bc", "(ab|c)*", "a*b*"]:
        rendered = to_regex(parse_regex(pattern))
        original = build_direct_dfa(pattern)
        reparsed = build_direct_dfa(rendered)
        for text in ["", "a", "b", "ab", "abb", "abc", "ad", "abcd", "c"]:
            assert original.match(text) == reparsed.match(text), (
                pattern,
                rendered,
                text,
            )


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("pattern", PRESET_PATTERNS)
def test_steps_endpoint_returns_a_usable_trace(pattern):
    response = client.post("/api/regex/steps", json={"pattern": pattern})
    assert response.status_code == 200
    body = response.json()
    assert body["schema"] == SCHEMA
    assert body["tool"] == "regex.direct"
    assert body["steps"]
    assert body["universe"]["kind"] == "position"
    # The page renders the final DFA and reveals it via highlight, so the
    # trace has to carry it.
    assert body["context"]["dfa"]["num_states"] >= 1
    assert body["context"]["tree"]["kind"]


def test_steps_endpoint_dfa_matches_the_direct_endpoint():
    """The Teach me view and the Result view must describe the same DFA,
    or the toggle contradicts itself.
    """
    pattern = "(a|b)*abb"
    steps = client.post("/api/regex/steps", json={"pattern": pattern}).json()
    direct = client.post("/api/regex/direct", json={"pattern": pattern}).json()
    assert steps["context"]["dfa"] == direct


def test_steps_endpoint_rejects_a_bad_pattern():
    response = client.post("/api/regex/steps", json={"pattern": "(a|"})
    assert response.status_code == 400
    assert "detail" in response.json()


def test_steps_endpoint_rejects_an_unknown_method():
    response = client.post(
        "/api/regex/steps", json={"pattern": "ab", "method": "telepathy"}
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Indirect method: Thompson's construction + subset construction
# ---------------------------------------------------------------------------


def test_thompson_fragments_account_for_every_nfa_state():
    """Every state in the finished NFA must have been introduced by some
    fragment step. A state nobody explains is a state the diagram shows
    appearing from nowhere.
    """
    tracer = trace_for("(a|b)*abb", "indirect")
    introduced = [
        state
        for step in tracer.steps
        if step["kind"].startswith("nfa.fragment.")
        for state in step["data"]["result"]
    ]
    assert sorted(introduced) == list(range(tracer.context["nfa"]["num_states"]))
    assert len(introduced) == len(set(introduced)), "a state was introduced twice"


def test_thompson_fragment_state_counts_follow_the_rules():
    """Thompson's rules each add a fixed number of states: two for a
    literal, epsilon, union and star, and none at all for concatenation.
    """
    expected = {"leaf": 2, "epsilon": 2, "union": 2, "star": 2, "concat": 0}
    for step in trace_for("(a|b)*ab?", "indirect").steps:
        if not step["kind"].startswith("nfa.fragment."):
            continue
        rule = step["kind"].rsplit(".", 1)[1]
        assert len(step["data"]["result"]) == expected[rule], step["kind"]


def test_fragments_are_emitted_before_subset_construction():
    phases = [s["phase"] for s in trace_for("(a|b)*abb", "indirect").steps]
    runs = [p for i, p in enumerate(phases) if i == 0 or phases[i - 1] != p]
    assert runs == ["nfa", "subset"]


def test_move_is_reported_separately_from_its_closure():
    """Conflating move(S, c) with the eps-closure that follows it is the
    classic way to get subset construction wrong, so they are separate
    steps and the closure must be a superset of the move.
    """
    steps = trace_for("(a|b)*abb", "indirect").steps
    pairs = 0
    for before, after in zip(steps, steps[1:]):
        if before["kind"] != "subset.move" or after["kind"] != "subset.closure":
            continue
        pairs += 1
        assert set(before["data"]["result"]) <= set(after["data"]["result"])
        assert after["data"]["source"] == before["data"]["result"]
    assert pairs > 0, "no move/closure pair in the trace"


def test_subset_closures_account_for_every_dfa_state():
    tracer = trace_for("a(b|c)*d", "indirect")
    dfa = tracer.context["dfa"]
    explained = {
        (s["data"]["state"], s["data"]["symbol"], s["data"]["target_state"])
        for s in tracer.steps
        if s["kind"] == "subset.closure" and "symbol" in s["data"]
    }
    actual = {(t["from"], t["symbol"], t["to"]) for t in dfa["transitions"]}
    assert explained == actual


def test_indirect_quizzes_are_drawn_from_the_nfa_states():
    tracer = trace_for("(a|b)*abb", "indirect")
    assert tracer.universe["kind"] == "nfa_state"
    assert tracer.universe["items"] == list(range(tracer.context["nfa"]["num_states"]))


def test_indirect_context_carries_the_nfa_for_the_graph():
    """The page renders the NFA alongside the DFA, so the trace has to
    carry it; nothing else returns both at once.
    """
    body = client.post(
        "/api/regex/steps", json={"pattern": "(a|b)*abb", "method": "indirect"}
    ).json()
    assert body["tool"] == "regex.indirect"
    nfa = body["context"]["nfa"]
    assert nfa["num_states"] > body["context"]["dfa"]["num_states"]
    assert any(t["symbol"] == "\u03b5" for t in nfa["transitions"])


@pytest.mark.parametrize("pattern", PRESET_PATTERNS)
def test_both_methods_agree_on_the_language(pattern):
    """The two Teach me views describe genuinely different machines - the
    indirect one usually has more states - so the thing that has to match
    is the language, not the shape. If these ever disagree, one of the two
    lessons is teaching a wrong automaton.
    """
    direct = build_direct_dfa(pattern)
    indirect = build_indirect_dfa(pattern)
    assert direct.alphabet == indirect.alphabet

    # Exercise the alphabet directly rather than with a fixed word list,
    # so each pattern is tested on strings it can actually be picky about.
    words = [""] + list(direct.alphabet)
    for _ in range(3):
        words += [w + symbol for w in words[-12:] for symbol in direct.alphabet]
    for word in words:
        assert direct.match(word) == indirect.match(word), (pattern, word)


def test_indirect_steps_endpoint_dfa_matches_the_indirect_endpoint():
    pattern = "(a|b)*abb"
    steps = client.post(
        "/api/regex/steps", json={"pattern": pattern, "method": "indirect"}
    ).json()
    plain = client.post("/api/regex/indirect", json={"pattern": pattern}).json()
    assert steps["context"]["dfa"] == plain


# ---------------------------------------------------------------------------
# DFA minimization: partition refinement
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("pattern", PRESET_PATTERNS)
def test_minimization_tracing_changes_nothing(pattern):
    """partition_trace predates the tracer and both the Result view and
    test_minimize_endpoint.py depend on it, so it has to come back
    byte-identical whether or not anyone is watching.
    """
    dfa = build_indirect_dfa(pattern)
    traced = minimize_dfa(dfa, tracer=Tracer(tool="dfa.minimize"))
    plain = minimize_dfa(dfa)
    assert traced.minimized.to_dict() == plain.minimized.to_dict()
    assert traced.state_mapping == plain.state_mapping
    assert traced.partition_trace == plain.partition_trace


@pytest.mark.parametrize("pattern", PRESET_PATTERNS)
def test_minimization_steps_satisfy_the_schema(pattern):
    steps = minimize_trace_for(pattern).steps
    assert steps
    for index, step in enumerate(steps):
        where = f"{pattern} step {index} ({step['kind']})"
        assert step["i"] == index, where
        assert len(step["explain"]) >= 20, where
        assert "result" in step["data"], where
        assert set(step["highlight"]) == set(HIGHLIGHT_KEYS), where


def test_a_group_that_survives_is_explained_too():
    """Why a group survives a round is half of partition refinement. A
    trace that only reported splits would read as a series of events
    with no reasoning between them.
    """
    steps = minimize_trace_for("(a|b)*abb").steps
    groups = [s for s in steps if s["kind"] == "min.group"]
    assert any(s["data"]["result"] is False for s in groups), "no survival reported"
    assert any(s["data"]["result"] is True for s in groups), "no split reported"


def test_a_split_names_the_symbol_that_caused_it():
    """The one fact partition_trace can never show: it records the
    before and after, never the reason.
    """
    for step in minimize_trace_for("(a|b)*abb").steps:
        if step["kind"] != "min.group" or step["data"]["result"] is not True:
            continue
        distinguishers = step["data"]["distinguishers"]
        assert distinguishers, step["title"]
        # The named symbols must be ones the states genuinely disagree on.
        for symbol in distinguishers:
            targets = {row[symbol] for row in step["data"]["signatures"].values()}
            assert len(targets) > 1, (step["title"], symbol)


def test_a_surviving_group_names_no_distinguisher():
    for step in minimize_trace_for("(a|b)*abb").steps:
        if step["kind"] != "min.group" or step["data"]["result"] is not False:
            continue
        assert step["data"]["distinguishers"] == []
        rows = list(step["data"]["signatures"].values())
        assert all(row == rows[0] for row in rows), step["title"]


def test_refinement_only_ever_splits():
    """Groups may divide but must never merge or lose states, so each
    round's partition is a refinement of the one before it.
    """
    steps = minimize_trace_for("[a-zA-Z][a-zA-Z0-9]*").steps
    snapshots = [
        [tuple(g) for g in s["data"]["groups"]]
        for s in steps
        if s["kind"] in {"min.init", "min.sweep", "min.stable"}
    ]
    for earlier, later in zip(snapshots, snapshots[1:]):
        assert len(later) >= len(earlier), "the partition got coarser"
        for group in later:
            parent = [g for g in earlier if set(group) <= set(g)]
            assert parent, f"{group} is not inside any earlier group"
        assert sorted(s for g in earlier for s in g) == sorted(
            s for g in later for s in g
        ), "a state went missing"


def test_merges_cover_every_state_exactly_once():
    tracer = minimize_trace_for("(a|b)*abb")
    merged = [
        state
        for step in tracer.steps
        if step["kind"] == "min.merge"
        for state in step["data"]["result"]
    ]
    original = tracer.context["original"]["num_states"]
    assert sorted(merged) == list(range(original))


def test_merge_steps_agree_with_the_state_mapping():
    """The groups are re-ordered after the refinement loop so the start
    state's group becomes q0, which means the merge steps, not the
    partition trace, are the authoritative group-to-state mapping.
    """
    tracer = minimize_trace_for("(a|b)*abb")
    mapping = tracer.context["state_mapping"]
    for step in tracer.steps:
        if step["kind"] != "min.merge":
            continue
        for state in step["data"]["result"]:
            assert mapping[str(state)] == step["data"]["minimized_state"]


def test_exactly_one_merge_claims_the_start_state():
    tracer = minimize_trace_for("(a|b)*abb")
    starts = [
        s for s in tracer.steps if s["kind"] == "min.merge" and s["data"]["is_start"]
    ]
    assert len(starts) == 1
    assert starts[0]["data"]["minimized_state"] == tracer.context["minimized"]["start"]


def test_minimize_steps_endpoint_matches_the_minimize_endpoint():
    pattern = "(a|b)*abb"
    body = {"pattern": pattern, "method": "indirect"}
    steps = client.post("/api/regex/minimize/steps", json=body).json()
    plain = client.post("/api/regex/minimize", json=body).json()
    assert steps["tool"] == "dfa.minimize"
    assert steps["context"]["original"] == plain["original"]
    assert steps["context"]["minimized"] == plain["minimized"]
    assert steps["context"]["state_mapping"] == plain["state_mapping"]
    assert steps["context"]["partition_trace"] == plain["partition_trace"]


def test_minimize_steps_endpoint_rejects_a_bad_pattern():
    response = client.post("/api/regex/minimize/steps", json={"pattern": "(a|"})
    assert response.status_code == 400


def test_minimizing_an_already_minimal_dfa_still_explains_itself():
    """The direct method is minimal by construction, so this is the
    "see, nothing changes" case - but it is not the "nothing happens"
    case, and the distinction is the lesson.

    The initial partition is only accepting vs non-accepting, which is
    coarse. Refinement still has to split it all the way down to
    singletons; that work is exactly how minimality gets *proven*. What
    makes the DFA already minimal is that no two states end up sharing a
    group, not that no group ever splits.
    """
    tracer = minimize_trace_for("(a|b)*abb", "direct")
    assert (
        tracer.context["original"]["num_states"]
        == (tracer.context["minimized"]["num_states"])
    )
    assert any(s["kind"] == "min.stable" for s in tracer.steps)

    merges = [s for s in tracer.steps if s["kind"] == "min.merge"]
    assert merges, "nothing was merged, not even trivially"
    assert all(len(s["data"]["result"]) == 1 for s in merges), (
        "an already-minimal DFA must end with every group a singleton"
    )


# ---------------------------------------------------------------------------
# Compiler pipeline: lexing and execution
# ---------------------------------------------------------------------------

from app.compiler.codegen import generate_code  # noqa: E402
from app.compiler.interpreter import run_program  # noqa: E402
from app.compiler.lexer import tokenize  # noqa: E402
from app.compiler.optimizer import optimize as run_optimizer  # noqa: E402
from app.compiler.parser import parse  # noqa: E402
from app.compiler.tac_generator import generate_tac  # noqa: E402

PROGRAM = "int x = 2 + 3;\nwhile (x > 0) { print(x); x = x - 1; }"


def assemble(source: str):
    return generate_code(run_optimizer(generate_tac(parse(tokenize(source).tokens).program)).after_dce)


def lex_trace(source: str = PROGRAM) -> Tracer:
    tracer = Tracer(tool="compiler", title="lex")
    tokenize(source, tracer=tracer)
    return tracer


def vm_trace(source: str = PROGRAM) -> Tracer:
    tracer = Tracer(tool="compiler", title="run")
    run_program(assemble(source), tracer=tracer)
    return tracer


@pytest.mark.parametrize("source", [PROGRAM, "int a = 1;", 'print("hi");'])
def test_compiler_tracing_changes_nothing(source):
    assert tokenize(source, tracer=Tracer(tool="compiler")).to_dict() == (
        tokenize(source).to_dict()
    )
    assembly = assemble(source)
    traced = run_program(assembly, tracer=Tracer(tool="compiler"))
    plain = run_program(assembly)
    assert traced.to_dict() == plain.to_dict()


@pytest.mark.parametrize("make", [lex_trace, vm_trace])
def test_compiler_steps_satisfy_the_schema(make):
    steps = make().steps
    assert steps
    for index, step in enumerate(steps):
        where = f"step {index} ({step['kind']})"
        assert step["i"] == index, where
        assert len(step["explain"]) >= 20, where
        assert "result" in step["data"], where
        assert set(step["highlight"]) == set(HIGHLIGHT_KEYS), where


# -- lexer -------------------------------------------------------------------

def test_every_token_is_accounted_for_by_a_token_step():
    """Trivia is scanned but dropped before the parser sees it, so the
    trace has to report the skipped tokens too or whole stretches of
    source look like they vanished.
    """
    tracer = lex_trace()
    emitted = [
        s["data"]["result"]
        for s in tracer.steps
        if s["kind"] == "lex.token" and not s["data"]["skipped"]
    ]
    assert emitted == [t.value for t in tokenize(PROGRAM).tokens]
    assert any(
        s["kind"] == "lex.token" and s["data"]["skipped"] for s in tracer.steps
    ), "whitespace was never reported"


def test_token_steps_cover_the_source_exactly_once():
    covered = []
    for step in lex_trace().steps:
        if step["kind"] == "lex.token":
            covered += step["highlight"]["chars"]
    assert sorted(covered) == list(range(len(PROGRAM)))


def test_keywords_are_reported_as_a_reclassification():
    """Keywords have no pattern of their own; they fall out of
    IDENTIFIER and get renamed. That is a real step, not a detail.
    """
    step = next(
        s
        for s in lex_trace("int x;").steps
        if s["kind"] == "lex.token" and s["data"]["result"] == "int"
    )
    assert step["data"]["matched_as"] == "IDENTIFIER"
    assert step["data"]["token_type"] == "KEYWORD"
    assert step["data"]["reclassified"] is True


def test_the_winner_is_the_longest_candidate():
    for step in lex_trace().steps:
        if step["kind"] != "lex.compete":
            continue
        longest = max(c["length"] for c in step["data"]["candidates"])
        assert step["data"]["length"] == longest, step["title"]
        winner = next(
            c for c in step["data"]["candidates"] if c["type"] == step["data"]["result"]
        )
        assert winner["length"] == longest


def test_the_scan_walk_reaches_the_length_the_competition_promised():
    """The per-character replay must agree with the match it is
    replaying, or the animation tells a different story from the result.
    """
    steps = lex_trace().steps
    for i, step in enumerate(steps):
        if step["kind"] != "lex.compete":
            continue
        walk = []
        for later in steps[i + 1:]:
            if later["kind"] != "lex.scan":
                break
            walk.append(later)
        assert walk, step["title"]
        assert walk[-1]["data"]["best_length"] == step["data"]["length"], step["title"]


def test_an_unmatched_character_is_explained():
    tracer = lex_trace("int x = 1 @ 2;")
    errors = [s for s in tracer.steps if s["kind"] == "lex.error"]
    assert len(errors) == 1
    assert errors[0]["data"]["result"] == "@"


# -- virtual machine ---------------------------------------------------------

def test_vm_steps_follow_the_program_counter():
    """Each step's next_pc must be where the following step actually
    starts, or the listing's arrow would jump around at random.
    """
    steps = [s for s in vm_trace().steps if s["kind"] in {"vm.step", "vm.jump"}]
    for before, after in zip(steps, steps[1:]):
        assert before["data"]["next_pc"] == after["data"]["pc"], before["title"]


def test_vm_stack_is_continuous_between_steps():
    steps = [s for s in vm_trace().steps if s["kind"] in {"vm.step", "vm.jump"}]
    for before, after in zip(steps, steps[1:]):
        assert before["data"]["stack"] == after["data"]["stack_before"], before["title"]


def test_vm_trace_reproduces_the_real_output():
    tracer = vm_trace()
    printed = [
        line
        for step in tracer.steps
        for line in step["data"].get("printed", [])
    ]
    assert printed == run_program(assemble(PROGRAM)).output
    assert printed, "the program printed nothing, so this proves little"


def test_a_conditional_jump_reports_whether_it_jumped():
    jumps = [s for s in vm_trace().steps if s["kind"] == "vm.jump"]
    assert jumps, "the loop should have produced conditional jumps"
    for step in jumps:
        taken = step["data"]["result"]
        moved = step["data"]["next_pc"] != step["data"]["pc"] + 1
        assert taken is moved, step["title"]
        assert step["quiz"]["kind"] == "choice"


def test_the_loop_actually_loops_in_the_trace():
    """A while loop must revisit the same instruction, which is the one
    thing a straight-line listing can never show.
    """
    visited = [
        s["data"]["pc"] for s in vm_trace().steps if s["kind"] in {"vm.step", "vm.jump"}
    ]
    assert len(visited) > len(set(visited)), "no instruction ran twice"


def test_vm_halts_with_an_empty_stack():
    halt = next(s for s in vm_trace().steps if s["kind"] == "vm.halt")
    assert halt["data"]["stack"] == [], "operands were left behind"


def test_a_runaway_program_truncates_instead_of_exploding():
    """MAX_STEPS is 200,000; recording every one of those would be a
    payload nobody can load.
    """
    tracer = Tracer(tool="compiler", limit=50)
    run_program(assemble("int i = 0; while (i < 500) { i = i + 1; }"), tracer=tracer)
    assert len(tracer.steps) == 50
    assert tracer.truncated is True


# -- endpoint ----------------------------------------------------------------

def test_compiler_steps_endpoint_defaults_to_every_phase():
    body = client.post("/api/compiler/steps", json={"source": PROGRAM}).json()
    assert body["tool"] == "compiler"
    kinds = {s["kind"].split(".")[0] for s in body["steps"]}
    assert kinds == {"lex", "vm"}
    assert body["context"]["source"] == PROGRAM
    assert body["context"]["assembly"]


def test_compiler_steps_endpoint_honours_the_phase_filter():
    body = client.post(
        "/api/compiler/steps", json={"source": PROGRAM, "phases": ["run"]}
    ).json()
    assert {s["kind"].split(".")[0] for s in body["steps"]} == {"vm"}
    # Tokens still come back: the run phase needs them, and the UI shows
    # them next to the instruction listing.
    assert body["context"]["tokens"]


def test_compiler_steps_endpoint_rejects_an_uninstrumented_phase():
    response = client.post(
        "/api/compiler/steps", json={"source": "int x = 1;", "phases": ["parse"]}
    )
    assert response.status_code == 422


def test_compiler_steps_endpoint_survives_a_broken_program():
    """Every other compiler route reports errors as payload, not as an
    HTTP failure, and this one has to behave the same.
    """
    response = client.post(
        "/api/compiler/steps", json={"source": "int x = @@@;", "phases": ["lex"]}
    )
    assert response.status_code == 200
    assert response.json()["context"]["lex_errors"]


# ---------------------------------------------------------------------------
# Grammar: FIRST, FOLLOW and the LL(1) table
# ---------------------------------------------------------------------------

from app.grammar.analyzer import analyze_grammar  # noqa: E402

EXPRESSION_GRAMMAR = """E -> T E1
E1 -> + T E1 | eps
T -> F T1
T1 -> * F T1 | eps
F -> ( E ) | id"""

AMBIGUOUS_GRAMMAR = """S -> a B | a C
B -> b
C -> c"""


def grammar_trace(text: str = EXPRESSION_GRAMMAR) -> Tracer:
    tracer = Tracer(tool="grammar.ll1", title="grammar")
    analyze_grammar(text, tracer=tracer)
    return tracer


@pytest.mark.parametrize("text", [EXPRESSION_GRAMMAR, AMBIGUOUS_GRAMMAR])
def test_grammar_tracing_changes_nothing(text):
    assert analyze_grammar(text, tracer=Tracer(tool="g")) == analyze_grammar(text)


@pytest.mark.parametrize("text", [EXPRESSION_GRAMMAR, AMBIGUOUS_GRAMMAR])
def test_grammar_steps_satisfy_the_schema(text):
    steps = grammar_trace(text).steps
    assert steps
    for index, step in enumerate(steps):
        where = f"step {index} ({step['kind']})"
        assert step["i"] == index, where
        assert len(step["explain"]) >= 20, where
        assert "result" in step["data"], where
        assert set(step["highlight"]) == set(HIGHLIGHT_KEYS), where


def test_first_and_follow_match_the_textbook():
    """The classic expression grammar, straight out of the dragon book.
    If these disagree the tool is teaching the wrong sets.
    """
    result = analyze_grammar(EXPRESSION_GRAMMAR)
    assert result["first_sets"] == {
        "E": ["(", "id"],
        "E1": ["+", "ε"],
        "F": ["(", "id"],
        "T": ["(", "id"],
        "T1": ["*", "ε"],
    }
    assert result["follow_sets"] == {
        "E": ["$", ")"],
        "E1": ["$", ")"],
        "F": ["$", ")", "*", "+"],
        "T": ["$", ")", "+"],
        "T1": ["$", ")", "+"],
    }


def test_the_traced_sets_converge_to_the_final_answer():
    """Folding the steps must land exactly on what /analyze returns, or
    the Teach me view and the Result view disagree.
    """
    tracer = grammar_trace()
    first, follow = {}, {}
    for step in tracer.steps:
        if step["kind"] == "first.production":
            first[step["data"]["non_terminal"]] = step["data"]["current"]
        elif step["kind"] in {"follow.init", "follow.production"}:
            follow[step["data"]["non_terminal"]] = step["data"].get(
                "current", step["data"]["result"]
            )
    assert first == tracer.context["first_sets"]
    assert follow == tracer.context["follow_sets"]


def test_sets_only_ever_grow():
    """A fixed point that could shrink would never be guaranteed to
    terminate, so this is the property the whole loop rests on.
    """
    seen = {}
    for step in grammar_trace().steps:
        if step["kind"] not in {"first.production", "follow.production"}:
            continue
        key = (step["kind"], step["data"]["non_terminal"])
        current = set(step["data"]["current"])
        assert seen.get(key, set()) <= current, key
        seen[key] = current


def test_a_reported_production_always_added_something():
    """Most productions add nothing on most sweeps. Reporting those
    would bury the few that matter, so an emitted step must have grown
    a set.
    """
    for step in grammar_trace().steps:
        if step["kind"] in {"first.production", "follow.production"}:
            assert step["data"]["result"], step["title"]


def test_each_fixpoint_ends_with_a_sweep_that_changed_nothing():
    """Why the loop stops is half the lesson, so the final no-op sweep
    is reported rather than silently skipped.
    """
    steps = grammar_trace().steps
    for kind in ("first.sweep", "follow.sweep"):
        sweeps = [s for s in steps if s["kind"] == kind]
        assert sweeps, kind
        assert sweeps[-1]["data"]["result"] == 0, kind
        assert all(s["data"]["result"] > 0 for s in sweeps[:-1]), kind


def test_table_rows_rebuild_the_real_table():
    tracer = grammar_trace()
    rebuilt = {}
    for step in tracer.steps:
        if step["kind"] != "ll1.production":
            continue
        row = rebuilt.setdefault(step["data"]["non_terminal"], {})
        for terminal in step["data"]["result"]:
            row.setdefault(terminal, []).append(step["data"]["production"])
    assert rebuilt == tracer.context["ll1_table"]["table"]


def test_a_conflict_is_reported_as_its_own_step():
    tracer = grammar_trace(AMBIGUOUS_GRAMMAR)
    conflicts = [s for s in tracer.steps if s["kind"] == "ll1.conflict"]
    assert conflicts, "the ambiguous grammar produced no conflict step"
    assert len(conflicts) == len(tracer.context["ll1_table"]["conflicts"])
    done = next(s for s in tracer.steps if s["kind"] == "ll1.done")
    assert done["data"]["result"] == len(conflicts)


def test_an_ll1_grammar_ends_with_no_conflicts():
    done = next(s for s in grammar_trace().steps if s["kind"] == "ll1.done")
    assert done["data"]["result"] == 0


def test_grammar_quizzes_draw_from_the_terminals():
    tracer = grammar_trace()
    assert tracer.universe["kind"] == "terminal"
    assert "$" in tracer.universe["items"]
    for step in tracer.steps:
        if step["quiz"] and step["quiz"]["kind"] == "set":
            assert set(step["quiz"]["answer"]) <= set(step["quiz"]["universe"]), (
                step["title"]
            )


def test_grammar_steps_endpoint_matches_the_analyze_endpoint():
    body = {"grammar": EXPRESSION_GRAMMAR}
    steps = client.post("/api/grammar/steps", json=body).json()
    plain = client.post("/api/grammar/analyze", json=body).json()
    assert steps["tool"] == "grammar.ll1"
    for key in ("first_sets", "follow_sets", "ll1_table", "start_symbol"):
        assert steps["context"][key] == plain[key], key


def test_an_empty_right_hand_side_is_a_valid_epsilon_production():
    """"E ->" is not a syntax error: an empty right-hand side is how
    this grammar format spells an epsilon production.
    """
    body = client.post("/api/grammar/steps", json={"grammar": "E ->"}).json()
    assert body["context"]["first_sets"] == {"E": ["ε"]}


def test_grammar_steps_endpoint_rejects_a_bad_grammar():
    response = client.post(
        "/api/grammar/steps", json={"grammar": "this line has no arrow"}
    )
    assert response.status_code == 400
