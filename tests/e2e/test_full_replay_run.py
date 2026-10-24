"""End-to-end tests for a complete VERIQ engineering run in replay mode.
"""

import time
import pytest
from fastapi.testclient import TestClient


def test_e2e_complete_engineering_run(api_client: TestClient):
    # 1. Create run
    payload = {
        "title": "E2E Statistical Calculator Expansion",
        "description": "Implement standard_deviation with full test verification and boundary safeguards",
        "sample_name": "calculator",
        "enable_research": True,
        "max_repair_attempts": 1,
        "mode": "replay",
    }

    create_resp = api_client.post("/api/runs", json=payload)
    assert create_resp.status_code == 200
    run_id = create_resp.json()["run_id"]

    # 2. Poll until terminal state (max 10 seconds)
    terminal_status = None
    for _ in range(20):
        time.sleep(0.5)
        resp = api_client.get(f"/api/runs/{run_id}")
        assert resp.status_code == 200
        run_data = resp.json()
        if run_data["status"] in ("COMPLETED", "FAILED", "VERIFICATION_FAILED"):
            terminal_status = run_data["status"]
            break

    assert terminal_status == "COMPLETED", f"Expected COMPLETED but got {terminal_status}"

    # 3. Verify Verification Ledger
    ledger_resp = api_client.get(f"/api/runs/{run_id}/ledger")
    assert ledger_resp.status_code == 200
    ledger = ledger_resp.json()
    assert ledger["total_claims"] == 6
    assert ledger["verified_count"] >= 4
    assert ledger["failed_count"] == 0

    # 4. Verify Diff
    diff_resp = api_client.get(f"/api/runs/{run_id}/diff")
    assert diff_resp.status_code == 200
    diff_text = diff_resp.text
    assert "def standard_deviation" in diff_text

    # 5. Verify Markdown Report Download
    report_md_resp = api_client.get(f"/api/runs/{run_id}/report?format=markdown")
    assert report_md_resp.status_code == 200
    assert "VERIQ" in report_md_resp.text
    assert "Code is generated. Proof is earned." in report_md_resp.text

    # 6. Verify JSON Report Download
    report_json_resp = api_client.get(f"/api/runs/{run_id}/report?format=json")
    assert report_json_resp.status_code == 200
    assert report_json_resp.json()["veriq_version"] == "1.0.0"
