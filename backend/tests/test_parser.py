"""
Tests for Milestone 8's parser (app/compiler/parser.py) and the AST it
builds (app/compiler/ast_nodes.py).
"""

from app.compiler.lexer import tokenize
from app.compiler.parser import parse


def _parse(source):
    lex_result = tokenize(source)
    assert lex_result.errors == [], f"unexpected lex errors: {lex_result.errors}"
    return parse(lex_result.tokens)


def test_var_decl_without_initializer():
    result = _parse("int x;")
    assert result.errors == []
    stmt = result.program.statements[0]
    assert stmt.to_dict() == {
        "kind": "VarDecl", "var_type": "int", "name": "x", "init": None,
        "line": 1, "column": 1,
    }


def test_var_decl_with_initializer():
    result = _parse("int x = 5;")
    stmt = result.program.statements[0]
    assert stmt.init.to_dict()["value"] == "5"


def test_assignment():
    result = _parse("x = 5;")
    stmt = result.program.statements[0]
    assert stmt.to_dict()["kind"] == "Assignment"
    assert stmt.name == "x"


def test_arithmetic_precedence_multiplication_binds_tighter_than_addition():
    result = _parse("x = 2 + 3 * 4;")
    value = result.program.statements[0].value
    assert value.op == "+"
    assert value.left.value == "2"
    assert value.right.op == "*"
    assert value.right.left.value == "3"
    assert value.right.right.value == "4"


def test_parentheses_override_precedence():
    result = _parse("x = (2 + 3) * 4;")
    value = result.program.statements[0].value
    assert value.op == "*"
    assert value.left.op == "+"


def test_comparison_and_logical_operator_precedence():
    # a > b && c > d  must parse as (a > b) && (c > d), not a > (b && c) > d
    result = _parse("x = a > b && c > d;")
    value = result.program.statements[0].value
    assert value.op == "&&"
    assert value.left.op == ">"
    assert value.right.op == ">"


def test_unary_minus_and_not():
    result = _parse("x = -5;")
    value = result.program.statements[0].value
    assert value.op == "-" and value.operand.value == "5"

    result = _parse("x = !flag;")
    value = result.program.statements[0].value
    assert value.op == "!" and value.operand.name == "flag"


def test_if_else():
    result = _parse("if (x > 0) { y = 1; } else { y = 2; }")
    stmt = result.program.statements[0]
    assert stmt.to_dict()["kind"] == "IfStmt"
    assert len(stmt.then_block.statements) == 1
    assert stmt.else_block is not None
    assert len(stmt.else_block.statements) == 1


def test_if_without_else():
    result = _parse("if (x > 0) { y = 1; }")
    stmt = result.program.statements[0]
    assert stmt.else_block is None


def test_while_loop():
    result = _parse("while (x > 0) { x = x - 1; }")
    stmt = result.program.statements[0]
    assert stmt.to_dict()["kind"] == "WhileStmt"
    assert len(stmt.body.statements) == 1


def test_return_with_and_without_value():
    result = _parse("return x;")
    assert result.program.statements[0].value.name == "x"

    result = _parse("return;")
    assert result.program.statements[0].value is None


def test_function_call_with_arguments():
    result = _parse("y = foo(1, 2 + 3);")
    call = result.program.statements[0].value
    assert call.to_dict()["kind"] == "Call"
    assert call.callee == "foo"
    assert len(call.args) == 2
    assert call.args[1].op == "+"


def test_function_call_as_a_statement():
    result = _parse("foo();")
    stmt = result.program.statements[0]
    assert stmt.to_dict()["kind"] == "ExprStmt"
    assert stmt.expr.callee == "foo"
    assert stmt.expr.args == []


def test_boolean_and_string_literals():
    result = _parse('x = true; y = "hi";')
    assert result.program.statements[0].value.literal_type == "BOOL"
    assert result.program.statements[1].value.literal_type == "STRING"


def test_nested_blocks_and_full_program():
    source = """
    int x;
    x = 2 + 3 * 4;
    if (x > 10) {
        x = x - 1;
    } else {
        x = x + 1;
    }
    while (x > 0) {
        x = x - 1;
    }
    return x;
    """
    result = _parse(source)
    assert result.errors == []
    kinds = [s.to_dict()["kind"] for s in result.program.statements]
    assert kinds == ["VarDecl", "Assignment", "IfStmt", "WhileStmt", "ReturnStmt"]


# ---------------------------------------------------------------------------
# Error recovery
# ---------------------------------------------------------------------------

def test_missing_semicolon_is_reported_with_correct_position():
    lex_result = tokenize("int x\nx = 5;")
    result = parse(lex_result.tokens)
    assert len(result.errors) == 1
    assert result.errors[0].line == 2
    assert "';'" in result.errors[0].message


def test_parser_recovers_and_continues_after_an_error():
    # The broken statement's error is reported, and a later, valid
    # statement still parses correctly, proving the parser didn't just
    # stop after the first problem.
    source = "int x\nx = 5;\nint y;"
    lex_result = tokenize(source)
    result = parse(lex_result.tokens)
    assert len(result.errors) >= 1
    kinds = [s.to_dict()["kind"] for s in result.program.statements]
    assert "VarDecl" in kinds
    assert any(s.to_dict().get("name") == "y" for s in result.program.statements)


def test_unexpected_token_in_expression_is_reported():
    lex_result = tokenize(") x = 2;")
    result = parse(lex_result.tokens)
    assert len(result.errors) >= 1
    assert "Unexpected token" in result.errors[0].message


def test_to_dict_is_json_serializable():
    import json

    result = _parse("int x; if (x > 0) { x = x - 1; } while (x > 0) { x = x - 1; }")
    json.dumps(result.to_dict())
