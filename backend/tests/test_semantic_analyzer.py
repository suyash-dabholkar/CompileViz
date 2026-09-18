"""
Tests for Milestone 9's semantic analyzer (app/compiler/semantic_analyzer.py).
"""

from app.compiler.lexer import tokenize
from app.compiler.parser import parse
from app.compiler.semantic_analyzer import analyze


def _analyze(source):
    lex_result = tokenize(source)
    assert lex_result.errors == [], f"unexpected lex errors: {lex_result.errors}"
    parse_result = parse(lex_result.tokens)
    assert parse_result.errors == [], f"unexpected parse errors: {parse_result.errors}"
    return analyze(parse_result.program)


def _messages(result):
    return [e.message for e in result.errors]


# ---------------------------------------------------------------------------
# Declarations, scoping, and redeclaration
# ---------------------------------------------------------------------------

def test_valid_declaration_and_assignment_has_no_errors():
    result = _analyze("int x = 5; x = 10;")
    assert result.errors == []


def test_redeclaration_in_the_same_scope_is_an_error():
    result = _analyze("int x; int x;")
    assert len(result.errors) == 1
    assert "already declared" in result.errors[0].message


def test_shadowing_in_a_nested_block_is_allowed():
    result = _analyze("int x = 1; if (true) { int x = 2; }")
    assert result.errors == []


def test_variable_declared_inside_a_block_is_not_visible_outside_it():
    result = _analyze("if (true) { int x = 1; } x = 2;")
    assert len(result.errors) == 1
    assert "Undeclared variable 'x'" in result.errors[0].message


def test_undeclared_variable_use_in_assignment():
    result = _analyze("y = 10;")
    assert _messages(result) == ["Undeclared variable 'y'"]


def test_undeclared_variable_use_in_expression():
    result = _analyze("int x = y + 5;")
    assert _messages(result) == ["Undeclared variable 'y'"]


def test_undeclared_variable_does_not_cascade_into_a_second_error():
    # Only the root cause should be reported, not also a bogus
    # type-mismatch on the '+' once 'y' resolves to TYPE_ERROR.
    result = _analyze("int x = y + 5;")
    assert len(result.errors) == 1


# ---------------------------------------------------------------------------
# Type checking
# ---------------------------------------------------------------------------

def test_type_mismatch_on_declaration_initializer():
    result = _analyze('int x = "hello";')
    assert "type 'string'" in result.errors[0].message
    assert "type 'int'" in result.errors[0].message


def test_type_mismatch_on_assignment():
    result = _analyze('int x = 5; x = "hello";')
    assert len(result.errors) == 1
    assert "Cannot assign" in result.errors[0].message


def test_int_may_widen_to_float():
    result = _analyze("float f = 5;")
    assert result.errors == []


def test_float_may_not_narrow_to_int():
    result = _analyze("int x = 5.0;")
    assert len(result.errors) == 1


def test_condition_must_be_bool():
    result = _analyze("if (5) { int x; }")
    assert "Condition must be of type 'bool'" in result.errors[0].message


def test_while_condition_must_be_bool():
    result = _analyze("while (5) { int x; }")
    assert "Condition must be of type 'bool'" in result.errors[0].message


def test_valid_comparison_condition_has_no_errors():
    result = _analyze("if (5 > 3) { int x; }")
    assert result.errors == []


def test_arithmetic_requires_numeric_operands():
    result = _analyze('int x = 5 + true;')
    assert "cannot be applied" in result.errors[0].message


def test_string_concatenation_with_plus_is_allowed():
    result = _analyze('string s = "a" + "b";')
    assert result.errors == []


def test_string_subtraction_is_not_allowed():
    result = _analyze('string s = "a" - "b";')
    assert len(result.errors) == 1


def test_logical_operators_require_bool_operands():
    result = _analyze("bool b = 5 && true;")
    assert "requires 'bool' operands" in result.errors[0].message


def test_relational_operators_require_numeric_operands():
    result = _analyze("bool b = true > false;")
    assert "requires numeric operands" in result.errors[0].message


def test_unary_minus_requires_numeric_operand():
    result = _analyze("int x = -true;")
    assert "requires a numeric operand" in result.errors[0].message


def test_unary_not_requires_bool_operand():
    result = _analyze("bool b = !5;")
    assert "requires a 'bool' operand" in result.errors[0].message


def test_int_and_float_may_be_compared_for_equality():
    result = _analyze("bool b = 5 == 5.0;")
    assert result.errors == []


# ---------------------------------------------------------------------------
# Function calls (built-ins only, see module docstring)
# ---------------------------------------------------------------------------

def test_correct_arity_call_has_no_errors():
    result = _analyze("print(5);")
    assert result.errors == []


def test_wrong_arity_call_is_an_error():
    result = _analyze("print(1, 2);")
    assert "expects 1 argument(s), got 2" in result.errors[0].message


def test_call_with_no_arguments_when_one_is_required():
    result = _analyze("print();")
    assert "expects 1 argument(s), got 0" in result.errors[0].message


def test_call_to_undefined_function_is_an_error():
    result = _analyze("foo(5);")
    assert "Call to undefined function 'foo'" in result.errors[0].message


# ---------------------------------------------------------------------------
# Symbol table output
# ---------------------------------------------------------------------------

def test_symbols_are_collected_for_display():
    result = _analyze("int x = 1; float y = 2.0; if (true) { bool z = true; }")
    names = {s.name for s in result.symbols}
    assert names == {"x", "y", "z"}


def test_to_dict_is_json_serializable():
    import json

    result = _analyze("int x = 1; if (x > 0) { x = x - 1; } print(x);")
    json.dumps(result.to_dict())
