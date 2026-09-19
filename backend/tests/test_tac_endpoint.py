"""
Tests for Milestone 10's /api/compiler/tac endpoint.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_tac_endpoint_returns_instructions():
    response = client.post("/api/compiler/tac", json={"source": "x = 2 + 3 * 4;"})
    assert response.status_code == 200
    body = response.json()
    texts = [i["text"] for i in body["tac"]]
    assert texts == ["%t1 = 3 * 4", "%t2 = 2 + %t1", "x = %t2"]


def test_tac_endpoint_handles_if_else():
    response = client.post(
        "/api/compiler/tac",
        json={"source": "if (x > 0) { x = 1; } else { x = 2; }"},
    )
    body = response.json()
    texts = [i["text"] for i in body["tac"]]
    assert "IF_FALSE %t1 GOTO %L1" in texts
    assert "GOTO %L2" in texts


def test_tac_endpoint_still_returns_lower_level_results():
    response = client.post("/api/compiler/tac", json={"source": "int x = 1;"})
    body = response.json()
    assert body["ast"]["kind"] == "Program"
    assert body["semantic_errors"] == []
    assert len(body["symbols"]) == 1


def test_tac_endpoint_generates_tac_even_with_semantic_errors():
    # A semantic error (undeclared variable) shouldn't stop TAC from
    # being generated, it's still useful to see for a dashboard.
    response = client.post("/api/compiler/tac", json={"source": "y = 5;"})
    body = response.json()
    assert len(body["semantic_errors"]) == 1
    assert len(body["tac"]) == 1
