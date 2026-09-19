"""
Tests for Milestone 12's interpreter (app/compiler/interpreter.py).

These are the strongest correctness tests in the whole project: they
prove the full pipeline, lexer through code generation, actually
executes toy-language programs and produces the right output, not
just that each phase individually looks plausible.
"""

from app.compiler.codegen import generate_code
from app.compiler.interpreter import run_program
from app.compiler.lexer import tokenize
from app.compiler.optimizer import optimize
from app.compiler.parser import parse
from app.compiler.tac_generator import generate_tac


def _run(source):
    lex_result = tokenize(source)
    assert lex_result.errors == []
    parse_result = parse(lex_result.tokens)
    assert parse_result.errors == []
    tac = generate_tac(parse_result.program)
    optimized = optimize(tac).after_dce
    code = generate_code(optimized)
    return run_program(code)


def test_print_a_literal():
    result = _run("print(5);")
    assert result.output == ["5"]
    assert result.runtime_error is None


def test_arithmetic_is_computed_correctly():
    result = _run("print(2 + 3 * 4);")
    assert result.output == ["14"]


def test_variable_assignment_and_use():
    result = _run("int x = 10; x = x + 5; print(x);")
    assert result.output == ["15"]


def test_if_else_takes_the_correct_branch():
    result = _run("int x = 10; if (x > 5) { print(1); } else { print(0); }")
    assert result.output == ["1"]

    result = _run("int x = 2; if (x > 5) { print(1); } else { print(0); }")
    assert result.output == ["0"]


def test_while_loop_counts_down_correctly():
    result = _run("int x = 5; while (x > 0) { print(x); x = x - 1; }")
    assert result.output == ["5", "4", "3", "2", "1"]


def test_boolean_and_comparison_operators():
    result = _run("print(true && false); print(3 > 2); print(3 == 3);")
    assert result.output == ["false", "true", "true"]


def test_string_printing():
    result = _run('print("hello");')
    assert result.output == ["hello"]


def test_unary_minus_and_not():
    result = _run("print(-5); print(!true);")
    assert result.output == ["-5", "false"]


def test_multiple_print_arguments_are_space_separated():
    # print only formally takes 1 arg per BUILTIN_FUNCTIONS, but the
    # interpreter's CALL handling is written generally, this exercises
    # that path directly rather than through a real program.
    from app.compiler.codegen import Instr

    code = [
        Instr("PUSH_CONST", "1"),
        Instr("PUSH_CONST", "2"),
        Instr("CALL", "print", "2"),
        Instr("STORE", "%t1"),
    ]
    result = run_program(code)
    assert result.output == ["1 2"]


def test_division_by_zero_is_a_runtime_error_not_a_crash():
    from app.compiler.codegen import Instr

    code = [Instr("PUSH_CONST", "5"), Instr("PUSH_CONST", "0"), Instr("DIV")]
    result = run_program(code)
    assert result.runtime_error == "Division by zero."


def test_reading_an_unassigned_variable_is_a_runtime_error():
    from app.compiler.codegen import Instr

    code = [Instr("LOAD", "y")]
    result = run_program(code)
    assert "read before being assigned" in result.runtime_error


def test_infinite_loop_is_stopped_and_reported_not_hung():
    result = _run("int x = 1; while (x > 0) { x = x + 1; }")
    assert result.runtime_error is not None
    assert "infinite loop" in result.runtime_error.lower()


def test_final_variable_values_are_reported():
    result = _run("int x = 1; int y = 2; x = x + y;")
    assert result.variables["x"] == 3
    assert result.variables["y"] == 2


def test_internal_temps_are_excluded_from_reported_variables():
    result = _run("int x = 1 + 2;")
    assert all(not name.startswith("%") for name in result.variables)


def test_to_dict_is_json_serializable():
    import json

    result = _run("int x = 5; while (x > 0) { print(x); x = x - 1; }")
    json.dumps(result.to_dict())
