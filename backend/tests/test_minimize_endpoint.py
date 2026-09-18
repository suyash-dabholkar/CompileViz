"""
Tests for Milestone 6's /api/regex/minimize endpoint.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_minimize_endpoint_defaults_to_indirect_method():
    response = client.post("/api/regex/minimize", json={"pattern": "(a|b)*abb"})
    assert response.status_code == 200
    body = response.json()
    assert body["method"] == "indirect"
    assert body["original"]["num_states"] == 5
    assert body["minimized"]["num_states"] == 4


def test_minimize_endpoint_direct_method_is_a_noop():
    response = client.post(
        "/api/regex/minimize", json={"pattern": "(a|b)*abb", "method": "direct"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["original"]["num_states"] == body["minimized"]["num_states"] == 4


def test_minimize_endpoint_returns_state_mapping_and_trace():
    response = client.post("/api/regex/minimize", json={"pattern": "(a|b)*abb"})
    body = response.json()
    assert len(body["state_mapping"]) == 5  # every original state mapped
    assert len(body["partition_trace"]) >= 2  # at least initial split + stable round


def test_minimize_endpoint_rejects_invalid_regex():
    response = client.post("/api/regex/minimize", json={"pattern": "(a|b"})
    assert response.status_code == 400
