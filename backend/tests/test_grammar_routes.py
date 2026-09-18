"""
Tests for Milestone 5's grammar API (app/api/grammar_routes.py), going
through the actual HTTP route rather than calling app.grammar directly.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

EXPRESSION_GRAMMAR = "E -> T E2\nE2 -> + T E2 | eps\nT -> F T2\nT2 -> * F T2 | eps\nF -> ( E ) | id"


def test_analyze_endpoint_matches_textbook_grammar():
    response = client.post("/api/grammar/analyze", json={"grammar": EXPRESSION_GRAMMAR})
    assert response.status_code == 200
    body = response.json()
    assert body["start_symbol"] == "E"
    assert sorted(body["first_sets"]["E2"]) == sorted(["+", "\u03b5"])
    assert body["ll1_table"]["is_ll1"] is True
    assert body["ll1_table"]["conflicts"] == []


def test_analyze_endpoint_reports_conflicts():
    response = client.post(
        "/api/grammar/analyze", json={"grammar": "S -> A | B\nA -> a\nB -> a"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ll1_table"]["is_ll1"] is False
    assert len(body["ll1_table"]["conflicts"]) == 1
    assert body["ll1_table"]["conflicts"][0]["non_terminal"] == "S"


def test_analyze_endpoint_rejects_invalid_grammar():
    response = client.post("/api/grammar/analyze", json={"grammar": "S a b"})
    assert response.status_code == 400
    assert "detail" in response.json()


def test_analyze_endpoint_rejects_empty_grammar():
    response = client.post("/api/grammar/analyze", json={"grammar": ""})
    assert response.status_code == 422  # Pydantic min_length validation
