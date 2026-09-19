"""
Tests for Milestone 11's /api/compiler/optimize endpoint.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_optimize_endpoint_collapses_a_constant_expression():
    response = client.post(
        "/api/compiler/optimize", json={"source": "x = 2 + 3 * 4;"}
    )
    assert response.status_code == 200
    body = response.json()
    final_texts = [i["text"] for i in body["after_dce"]]
    assert final_texts == ["x = 14"]
    assert body["instructions_removed"] == 2


def test_optimize_endpoint_returns_every_stage():
    response = client.post(
        "/api/compiler/optimize", json={"source": "t = a + b; s = a + b;"}
    )
    body = response.json()
    assert len(body["original"]) == 4
    assert len(body["after_cse"]) < len(body["original"])


def test_optimize_endpoint_still_includes_earlier_phase_results():
    response = client.post("/api/compiler/optimize", json={"source": "int x = 1;"})
    body = response.json()
    assert body["ast"]["kind"] == "Program"
    assert body["semantic_errors"] == []
    assert len(body["symbols"]) == 1


def test_optimize_endpoint_never_breaks_control_flow():
    response = client.post(
        "/api/compiler/optimize",
        json={"source": "while (x > 0) { x = x - 1; } print(x);"},
    )
    body = response.json()
    ops = {i["op"] for i in body["after_dce"]}
    assert "IF_FALSE" in ops
    assert "GOTO" in ops
    assert "CALL" in ops
