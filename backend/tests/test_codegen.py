"""
Tests for Milestone 12's code generator (app/compiler/codegen.py).
"""

from app.compiler.codegen import generate_code
from app.compiler.lexer import tokenize
from app.compiler.parser import parse
from app.compiler.tac_generator import generate_tac


def _asm(source):
    lex_result = tokenize(source)
    assert lex_result.errors == []
    parse_result = parse(lex_result.tokens)
    assert parse_result.errors == []
    tac = generate_tac(parse_result.program)
    return [i.text() for i in generate_code(tac)]


def test_simple_assignment():
    assert _asm("x = 5;") == ["PUSH_CONST 5", "STORE x"]


def test_binary_op_pushes_both_operands_then_the_op():
    assert _asm("x = a + b;") == [
        "LOAD a", "LOAD b", "ADD", "STORE %t1",
        "LOAD %t1", "STORE x",
    ]


def test_unary_minus_and_not():
    assert _asm("x = -a;") == ["LOAD a", "NEG", "STORE %t1", "LOAD %t1", "STORE x"]
    assert _asm("x = !a;") == ["LOAD a", "NOT", "STORE %t1", "LOAD %t1", "STORE x"]


def test_string_literal_is_a_push_const_not_a_load():
    assert _asm('x = "hi";') == ['PUSH_CONST "hi"', "STORE x"]


def test_if_without_else_emits_conditional_jump_and_one_label():
    lines = _asm("if (x > 0) { y = 1; }")
    assert "JMP_FALSE %L1" in lines
    assert lines[-1] == "%L1:"


def test_while_loop_jumps_back():
    lines = _asm("while (x > 0) { x = x - 1; }")
    assert lines[0] == "%L1:"
    assert "JMP %L1" in lines


def test_function_call_pushes_args_then_calls():
    lines = _asm("print(1, 2);")
    assert lines == [
        "PUSH_CONST 1", "PUSH_CONST 2", "CALL print, 2", "STORE %t1",
    ]


def test_return_with_and_without_value():
    assert _asm("return 5;") == ["PUSH_CONST 5", "RET"]
    assert _asm("return;") == ["RET"]


def test_to_dict_is_json_serializable():
    import json

    lines = generate_code(
        generate_tac(
            parse(tokenize("int x = 1; while (x > 0) { x = x - 1; } print(x);").tokens).program
        )
    )
    json.dumps([i.to_dict() for i in lines])
