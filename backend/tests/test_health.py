"""
Milestone 1 sanity test. Every later milestone adds its own test file
next to this one (test_direct_dfa.py, test_ll1_table.py, ...), and CI
runs all of them on every pull request.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "compileviz-backend"}
