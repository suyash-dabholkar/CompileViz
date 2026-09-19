"""
Tests for Milestone 10's TAC generator (app/compiler/tac_generator.py).
"""

from app.compiler.lexer import tokenize
from app.compiler.parser import parse
from app.compiler.tac_generator import generate_tac


def _tac_lines(source):
    lex_result = tokenize(source)
    assert lex_result.errors == []
    parse_result = parse(lex_result.tokens)
    assert parse_result.errors == []
    return [instr.text() for instr in generate_tac(parse_result.program)]


def test_simple_assignment():
    assert _tac_lines("x = 5;") == ["x = 5"]


def test_arithmetic_respects_precedence():
    lines = _tac_lines("x = 2 + 3 * 4;")
    # 3 * 4 must be computed into a temp BEFORE it's added to 2, that's
    # what proves precedence survived into the linear instruction list.
    assert lines == ["%t1 = 3 * 4", "%t2 = 2 + %t1", "x = %t2"]


def test_var_decl_without_initializer_emits_nothing():
    assert _tac_lines("int x;") == []


def test_var_decl_with_initializer():
    assert _tac_lines("int x = 5;") == ["x = 5"]


def test_unary_minus_and_not():
    assert _tac_lines("x = -5;") == ["%t1 = -5", "x = %t1"]
    assert _tac_lines("x = !flag;") == ["%t1 = !flag", "x = %t1"]


def test_if_without_else_uses_one_label():
    lines = _tac_lines("if (x > 0) { x = 1; }")
    assert lines == [
        "%t1 = x > 0",
        "IF_FALSE %t1 GOTO %L1",
        "x = 1",
        "%L1:",
    ]


def test_if_with_else_uses_two_labels_and_a_goto():
    lines = _tac_lines("if (x > 0) { x = 1; } else { x = 2; }")
    assert lines == [
        "%t1 = x > 0",
        "IF_FALSE %t1 GOTO %L1",
        "x = 1",
        "GOTO %L2",
        "%L1:",
        "x = 2",
        "%L2:",
    ]


def test_while_loop_jumps_back_to_the_top():
    lines = _tac_lines("while (x > 0) { x = x - 1; }")
    assert lines == [
        "%L1:",
        "%t1 = x > 0",
        "IF_FALSE %t1 GOTO %L2",
        "%t2 = x - 1",
        "x = %t2",
        "GOTO %L1",
        "%L2:",
    ]


def test_function_call_emits_param_then_call():
    lines = _tac_lines("print(1 + 2);")
    assert lines == ["%t1 = 1 + 2", "PARAM %t1", "%t2 = CALL print, 1"]


def test_call_with_no_arguments():
    lines = _tac_lines("print();")
    assert lines == ["%t1 = CALL print, 0"]


def test_return_with_and_without_value():
    assert _tac_lines("return x;") == ["RETURN x"]
    assert _tac_lines("return;") == ["RETURN"]


def test_labels_and_temps_are_unique_across_a_whole_program():
    lines = _tac_lines(
        "if (x > 0) { x = 1; } if (x > 0) { x = 2; }"
    )
    # Two separate if-statements must not reuse %L1 or produce
    # colliding labels.
    label_lines = [l for l in lines if l.endswith(":")]
    assert label_lines == ["%L1:", "%L2:"]


def test_nested_if_inside_while():
    lines = _tac_lines("while (x > 0) { if (x > 5) { x = 0; } }")
    assert lines == [
        "%L1:",
        "%t1 = x > 0",
        "IF_FALSE %t1 GOTO %L2",
        "%t2 = x > 5",
        "IF_FALSE %t2 GOTO %L3",
        "x = 0",
        "%L3:",
        "GOTO %L1",
        "%L2:",
    ]


def test_to_dict_is_json_serializable():
    import json

    lex_result = tokenize("int x = 1; while (x > 0) { x = x - 1; } print(x);")
    parse_result = parse(lex_result.tokens)
    instrs = generate_tac(parse_result.program)
    json.dumps([i.to_dict() for i in instrs])
