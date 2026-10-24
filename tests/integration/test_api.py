"""Integration tests for VERIQ REST API endpoints.
"""

from fastapi.testclient import TestClient


def test_api_health(api_client: TestClient):
    resp = api_client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == "VERIQ"
    assert "sandbox" in data


def test_api_providers_status(api_client: TestClient):
    resp = api_client.get("/api/providers/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "nebius" in data
    assert "tavily" in data


def test_api_models_catalog(api_client: TestClient):
    resp = api_client.get("/api/models")
    assert resp.status_code == 200
    data = resp.json()
    assert "FAST" in data["tiers"]
    assert "STANDARD" in data["tiers"]
    assert "ESCALATION" in data["tiers"]


def test_api_samples(api_client: TestClient):
    resp = api_client.get("/api/samples")
    assert resp.status_code == 200
    samples = resp.json()
    assert len(samples) > 0
    assert samples[0]["name"] == "calculator"


def test_api_benchmarks(api_client: TestClient):
    resp = api_client.get("/api/benchmarks")
    assert resp.status_code == 200
    data = resp.json()
    assert data["task_count"] == 5
    assert data["routed_pass_rate"] >= data["baseline_pass_rate"]


def test_api_create_and_inspect_run(api_client: TestClient):
    payload = {
        "title": "API Test Task",
        "description": "Integration test task specification",
        "sample_name": "calculator",
        "enable_research": False,
        "max_repair_attempts": 1,
        "mode": "replay",
    }
    resp = api_client.post("/api/runs", json=payload)
    assert resp.status_code == 200
    run = resp.json()
    run_id = run["run_id"]
    assert run_id.startswith("RUN-")

    # Get run details
    get_resp = api_client.get(f"/api/runs/{run_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["run_id"] == run_id

    # List runs
    list_resp = api_client.get("/api/runs")
    assert list_resp.status_code == 200
    assert any(r["run_id"] == run_id for r in list_resp.json())
