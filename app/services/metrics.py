"""System and Operational Telemetry for VERIQ.
Aggregates actual metrics strictly from persisted database records.
"""

from typing import Dict, Any, List
from app.storage.database import get_db_connection
from app.schemas.evidence import ClaimStatus


class MetricsService:
    @staticmethod
    def get_overview_statistics() -> Dict[str, Any]:
        """Calculates verified system metrics from actual SQLite database records."""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Total runs
            cursor.execute("SELECT COUNT(*) as total FROM runs")
            total_runs = cursor.fetchone()["total"]

            # Runs by status
            cursor.execute("SELECT status, COUNT(*) as count FROM runs GROUP BY status")
            runs_by_status = {row["status"]: row["count"] for row in cursor.fetchall()}

            # Execution modes
            cursor.execute("SELECT execution_mode, COUNT(*) as count FROM runs GROUP BY execution_mode")
            modes = {row["execution_mode"]: row["count"] for row in cursor.fetchall()}

            # Claims statistics
            cursor.execute("SELECT status, COUNT(*) as count FROM claims GROUP BY status")
            claims_by_status = {row["status"]: row["count"] for row in cursor.fetchall()}

            total_claims = sum(claims_by_status.values())
            verified_claims = claims_by_status.get(ClaimStatus.VERIFIED.value, 0)
            failed_claims = claims_by_status.get(ClaimStatus.FAILED.value, 0)
            unresolved_claims = claims_by_status.get(ClaimStatus.UNRESOLVED.value, 0)
            supported_claims = claims_by_status.get(ClaimStatus.SUPPORTED.value, 0)

            verification_rate = (
                round((verified_claims / total_claims) * 100.0, 1) if total_claims > 0 else 0.0
            )

            # Average duration of completed runs
            cursor.execute("SELECT AVG(duration_seconds) as avg_dur FROM runs WHERE status = 'COMPLETED'")
            row = cursor.fetchone()
            avg_duration = round(row["avg_dur"] or 0.0, 2)

            return {
                "total_runs": total_runs,
                "runs_by_status": runs_by_status,
                "execution_modes": modes,
                "total_claims": total_claims,
                "verified_claims": verified_claims,
                "supported_claims": supported_claims,
                "failed_claims": failed_claims,
                "unresolved_claims": unresolved_claims,
                "verification_rate_percent": verification_rate,
                "avg_completed_duration_seconds": avg_duration,
            }


metrics_service = MetricsService()
