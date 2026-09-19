"""
Tests for Milestone 12's /api/compiler/codegen endpoint, the complete
six-phase pipeline including actually running the program.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_codegen_endpoint_runs_a_simple_program():
    response = client.post(
        "/api/compiler/codegen", json={"source": "int x = 5; print(x);"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["run_result"]["output"] == ["5"]
    assert body["run_result"]["runtime_error"] is None


def test_codegen_endpoint_runs_a_loop_correctly():
    response = client.post(
        "/api/compiler/codegen",
        json={"source": "int x = 3; while (x > 0) { print(x); x = x - 1; }"},
    )
    body = response.json()
    assert body["run_result"]["output"] == ["3", "2", "1"]


def test_codegen_endpoint_reports_runtime_errors():
    response = client.post(
        "/api/compiler/codegen",
        json={"source": "int x = 1; while (x > 0) { x = x + 1; }"},
    )
    body = response.json()
    assert body["run_result"]["runtime_error"] is not None


def test_codegen_endpoint_still_includes_earlier_phase_results():
    response = client.post("/api/compiler/codegen", json={"source": "int x = 1;"})
    body = response.json()
    assert body["ast"]["kind"] == "Program"
    assert len(body["assembly"]) > 0


def test_codegen_endpoint_includes_final_variable_values():
    response = client.post(
        "/api/compiler/codegen", json={"source": "int x = 2; x = x + 3;"}
    )
    body = response.json()
    assert body["run_result"]["variables"]["x"] == "5"
