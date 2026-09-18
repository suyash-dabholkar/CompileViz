"""
Tests for Milestone 7's /api/compiler/tokenize endpoint.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_tokenize_endpoint_returns_tokens():
    response = client.post("/api/compiler/tokenize", json={"source": "int x; x = 5;"})
    assert response.status_code == 200
    body = response.json()
    assert body["errors"] == []
    assert body["tokens"][0] == {"type": "KEYWORD", "value": "int", "line": 1, "column": 1}


def test_tokenize_endpoint_returns_errors_as_200_not_400():
    # Lexical errors are a normal outcome of tokenizing, not a bad
    # request, this must NOT be a 4xx.
    response = client.post("/api/compiler/tokenize", json={"source": "x = 1; @ y;"})
    assert response.status_code == 200
    body = response.json()
    assert len(body["errors"]) == 1
    assert body["errors"][0]["message"] == "Unexpected character '@'"


def test_tokenize_endpoint_handles_full_program():
    source = "int x;\nx = 2 + 3 * 4;\nif (x > 10) { x = x - 1; }"
    response = client.post("/api/compiler/tokenize", json={"source": source})
    assert response.status_code == 200
    body = response.json()
    assert body["errors"] == []
    assert len(body["tokens"]) > 10
