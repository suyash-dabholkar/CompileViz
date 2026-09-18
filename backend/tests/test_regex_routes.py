"""
Tests for Milestone 4's regex playground API (app/api/regex_routes.py).

These go through FastAPI's TestClient, hitting the actual HTTP routes,
not the underlying app.automata functions directly (those already have
their own tests). The point here is to check the wiring: correct status
codes, correct JSON shape, and that invalid input is translated into a
proper 400 instead of a raw Python exception or a 500.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# /api/regex/direct
# ---------------------------------------------------------------------------

def test_direct_endpoint_returns_dfa_shape():
    response = client.post("/api/regex/direct", json={"pattern": "a*b"})
    assert response.status_code == 200
    body = response.json()
    assert "states" in body
    assert "transitions" in body
    assert body["num_states"] == len(body["states"])
    assert isinstance(body["accepting"], list)


def test_direct_endpoint_matches_textbook_example():
    response = client.post("/api/regex/direct", json={"pattern": "(a|b)*abb"})
    assert response.status_code == 200
    assert response.json()["num_states"] == 4


def test_direct_endpoint_rejects_invalid_regex():
    response = client.post("/api/regex/direct", json={"pattern": "(a|b"})
    assert response.status_code == 400
    assert "detail" in response.json()


def test_direct_endpoint_rejects_empty_pattern():
    response = client.post("/api/regex/direct", json={"pattern": ""})
    assert response.status_code == 422  # Pydantic min_length validation


# ---------------------------------------------------------------------------
# /api/regex/indirect
# ---------------------------------------------------------------------------

def test_indirect_endpoint_returns_dfa_shape():
    response = client.post("/api/regex/indirect", json={"pattern": "a*b"})
    assert response.status_code == 200
    body = response.json()
    assert "states" in body
    assert "transitions" in body


def test_indirect_endpoint_rejects_invalid_regex():
    response = client.post("/api/regex/indirect", json={"pattern": "[a-z"})
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# /api/regex/thompson
# ---------------------------------------------------------------------------

def test_thompson_endpoint_returns_nfa_shape():
    response = client.post("/api/regex/thompson", json={"pattern": "a|b"})
    assert response.status_code == 200
    body = response.json()
    assert "start" in body
    assert "accept" in body
    assert "transitions" in body
    # at least one epsilon-transition should appear, since union always
    # introduces branch/join epsilon-transitions
    assert any(t["symbol"] == "\u03b5" for t in body["transitions"])


# ---------------------------------------------------------------------------
# /api/regex/match
# ---------------------------------------------------------------------------

def test_match_endpoint_accepts_with_direct_method():
    response = client.post(
        "/api/regex/match",
        json={"pattern": "[a-zA-Z][a-zA-Z0-9]*", "text": "x1", "method": "direct"},
    )
    assert response.status_code == 200
    assert response.json()["matches"] is True


def test_match_endpoint_rejects_with_indirect_method():
    response = client.post(
        "/api/regex/match",
        json={"pattern": "[0-9]+", "text": "12a", "method": "indirect"},
    )
    assert response.status_code == 200
    assert response.json()["matches"] is False


def test_match_endpoint_defaults_to_direct_method():
    response = client.post("/api/regex/match", json={"pattern": "a+", "text": "aaa"})
    assert response.status_code == 200
    assert response.json()["method"] == "direct"


# ---------------------------------------------------------------------------
# /api/regex/compare
# ---------------------------------------------------------------------------

def test_compare_endpoint_returns_both_methods():
    response = client.post(
        "/api/regex/compare", json={"pattern": "(a|b)*abb", "runs": 5}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["direct_method"]["state_count"] == 4
    assert body["indirect_method"]["state_count"] >= 1
    assert body["direct_method"]["avg_build_time_seconds"] > 0
    assert body["runs"] == 5


def test_compare_endpoint_rejects_too_many_runs():
    response = client.post(
        "/api/regex/compare", json={"pattern": "a", "runs": 1000}
    )
    assert response.status_code == 422  # Pydantic le=50 validation


def test_compare_endpoint_uses_default_runs_when_omitted():
    response = client.post("/api/regex/compare", json={"pattern": "a"})
    assert response.status_code == 200
    assert response.json()["runs"] == 10
