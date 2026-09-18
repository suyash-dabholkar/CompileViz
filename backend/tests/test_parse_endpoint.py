"""
Tests for Milestone 8's /api/compiler/parse endpoint.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_parse_endpoint_returns_ast():
    response = client.post("/api/compiler/parse", json={"source": "int x; x = 5;"})
    assert response.status_code == 200
    body = response.json()
    assert body["lex_errors"] == []
    assert body["parse_errors"] == []
    assert body["ast"]["kind"] == "Program"
    assert body["ast"]["statements"][0]["kind"] == "VarDecl"


def test_parse_endpoint_reports_syntax_errors_as_200():
    response = client.post("/api/compiler/parse", json={"source": "int x\nx = 5;"})
    assert response.status_code == 200
    body = response.json()
    assert len(body["parse_errors"]) == 1


def test_parse_endpoint_handles_full_program():
    source = "int x;\nif (x > 0) { x = x - 1; } else { x = x + 1; }"
    response = client.post("/api/compiler/parse", json={"source": source})
    assert response.status_code == 200
    body = response.json()
    assert body["ast"]["statements"][1]["kind"] == "IfStmt"
