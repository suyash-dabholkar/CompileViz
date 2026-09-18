"""
Tests for Milestone 7's lexer (app/compiler/lexer.py).
"""

from app.compiler.lexer import tokenize


def _types(tokens):
    return [t.type for t in tokens]


def _pairs(tokens):
    return [(t.type, t.value) for t in tokens]


def test_simple_declaration_and_assignment():
    result = tokenize("int x; x = 5;")
    assert result.errors == []
    assert _pairs(result.tokens) == [
        ("KEYWORD", "int"),
        ("IDENTIFIER", "x"),
        ("SEMICOLON", ";"),
        ("IDENTIFIER", "x"),
        ("ASSIGN", "="),
        ("INT", "5"),
        ("SEMICOLON", ";"),
    ]


def test_keywords_are_not_misclassified_as_identifiers():
    result = tokenize("if else while return def true false int float bool string")
    assert all(t.type == "KEYWORD" for t in result.tokens)


def test_identifier_that_merely_starts_like_a_keyword_stays_an_identifier():
    # "ifX" must not be split into KEYWORD "if" + IDENTIFIER "X", maximal
    # munch should consume the whole thing as one IDENTIFIER.
    result = tokenize("ifX whileLoop")
    assert _pairs(result.tokens) == [
        ("IDENTIFIER", "ifX"),
        ("IDENTIFIER", "whileLoop"),
    ]


def test_float_vs_int():
    result = tokenize("3.14 42 7.0")
    assert _pairs(result.tokens) == [
        ("FLOAT", "3.14"),
        ("INT", "42"),
        ("FLOAT", "7.0"),
    ]


def test_string_literal_stops_at_closing_quote():
    result = tokenize('"hello world" x')
    assert _pairs(result.tokens) == [
        ("STRING", '"hello world"'),
        ("IDENTIFIER", "x"),
    ]


def test_string_literal_may_contain_hash():
    # The exact case that exposed the end-marker collision bug.
    result = tokenize('"a # b"')
    assert result.errors == []
    assert _pairs(result.tokens) == [("STRING", '"a # b"')]


def test_multi_char_operators_win_over_single_char_prefixes():
    result = tokenize("== != <= >= && ||")
    assert _types(result.tokens) == ["EQ", "NE", "LE", "GE", "AND", "OR"]


def test_single_char_operators_when_not_part_of_a_longer_one():
    result = tokenize("= < > + - * / !")
    assert _types(result.tokens) == [
        "ASSIGN", "LT", "GT", "PLUS", "MINUS", "STAR", "SLASH", "NOT",
    ]


def test_comments_are_skipped_and_stop_at_newline():
    result = tokenize("x = 1; // this is a comment\ny = 2;")
    assert result.errors == []
    assert _pairs(result.tokens) == [
        ("IDENTIFIER", "x"),
        ("ASSIGN", "="),
        ("INT", "1"),
        ("SEMICOLON", ";"),
        ("IDENTIFIER", "y"),
        ("ASSIGN", "="),
        ("INT", "2"),
        ("SEMICOLON", ";"),
    ]


def test_whitespace_is_skipped_but_still_advances_line_and_column():
    result = tokenize("x\n  y")
    assert [(t.value, t.line, t.column) for t in result.tokens] == [
        ("x", 1, 1),
        ("y", 2, 3),
    ]


def test_full_if_else_program_tokenizes_cleanly():
    source = """
    int x;
    x = 2 + 3 * 4;
    if (x > 10) {
        x = x - 1;
    } else {
        x = x + 1;
    }
    """
    result = tokenize(source)
    assert result.errors == []
    assert result.tokens[0].type == "KEYWORD" and result.tokens[0].value == "int"
    assert "IF" not in _types(result.tokens)  # keywords keep type KEYWORD, not IF
    assert _types(result.tokens).count("KEYWORD") == 3  # "int", "if", "else"


def test_invalid_character_is_reported_and_lexing_continues():
    result = tokenize("x = 1; @ y = 2;")
    assert len(result.errors) == 1
    assert result.errors[0].message == "Unexpected character '@'"
    # Lexing must continue past the bad character rather than stopping.
    assert ("IDENTIFIER", "y") in _pairs(result.tokens)
    assert ("INT", "2") in _pairs(result.tokens)


def test_multiple_invalid_characters_are_all_reported_in_one_pass():
    # '#' is only valid inside a STRING literal's body; on its own it's
    # just as unrecognized as '@', so a bare '#' should also be flagged.
    result = tokenize("a @ b # c")
    messages = [e.message for e in result.errors]
    assert "Unexpected character '@'" in messages
    assert "Unexpected character '#'" in messages
    assert len(result.errors) == 2


def test_error_positions_are_correct():
    result = tokenize("x\n  @ y")
    assert result.errors[0].line == 2
    assert result.errors[0].column == 3


def test_to_dict_is_json_serializable():
    import json

    result = tokenize('int x; x = "hi"; // comment\nif (x) { x = x + 1; }')
    json.dumps(result.to_dict())
