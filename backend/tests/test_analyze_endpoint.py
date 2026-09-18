"""
Tests for Milestone 9's /api/compiler/analyze endpoint.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_analyze_endpoint_returns_symbols_and_no_errors_for_valid_program():
    response = client.post(
        "/api/compiler/analyze", json={"source": "int x = 5; x = x + 1;"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["semantic_errors"] == []
    assert len(body["symbols"]) == 1
    assert body["symbols"][0]["name"] == "x"
    assert body["symbols"][0]["type"] == "int"


def test_analyze_endpoint_reports_undeclared_variable():
    response = client.post("/api/compiler/analyze", json={"source": "y = 10;"})
    assert response.status_code == 200
    body = response.json()
    assert len(body["semantic_errors"]) == 1
    assert "Undeclared variable 'y'" in body["semantic_errors"][0]["message"]


def test_analyze_endpoint_reports_type_mismatch():
    response = client.post(
        "/api/compiler/analyze", json={"source": 'int x = "hello";'}
    )
    body = response.json()
    assert len(body["semantic_errors"]) == 1


def test_analyze_endpoint_reports_call_arity_error():
    response = client.post("/api/compiler/analyze", json={"source": "print(1, 2);"})
    body = response.json()
    assert "expects 1 argument(s), got 2" in body["semantic_errors"][0]["message"]


def test_analyze_endpoint_still_includes_ast_and_lower_level_errors():
    response = client.post("/api/compiler/analyze", json={"source": "int x\nx = 5;"})
    body = response.json()
    assert body["ast"]["kind"] == "Program"
    assert len(body["parse_errors"]) == 1
