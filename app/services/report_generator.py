"""Verification Report Generator for VERIQ.
Produces comprehensive, inspectable JSON and Markdown engineering audit reports.
"""

import json
from typing import Dict, Any
from app.schemas.runs import RunResponse
from app.schemas.evidence import VerificationLedgerSummary, ClaimStatus


class ReportGenerator:
    @staticmethod
    def generate_markdown_report(run: RunResponse, ledger: VerificationLedgerSummary) -> str:
        """Generates a submission-grade Markdown audit report."""
        v_rate = (
            round((ledger.verified_count / ledger.total_claims) * 100.0, 1)
            if ledger.total_claims > 0
            else 0.0
        )

        md = []
        md.append("# VERIQ — Engineering Verification Report")
        md.append("**Tagline: Code is generated. Proof is earned.**\n")
        md.append(f"> **Run ID**: `{run.run_id}`  ")
        md.append(f"> **Execution Mode**: `{run.execution_mode}`  ")
        md.append(f"> **Status**: `{run.status.value}`  ")
        md.append(f"> **Duration**: `{run.duration_seconds}s`  ")
        md.append(f"> **Task**: {run.task_title}\n")

        md.append("## Executive Summary\n")
        md.append(
            f"VERIQ evaluated task **{run.task_title}** using an evidence-driven verification engine. "
            f"Out of **{ledger.total_claims}** total claims, **{ledger.verified_count}** were deterministically VERIFIED, "
            f"**{ledger.supported_count}** are SUPPORTED by documentation, "
            f"**{ledger.failed_count}** FAILED checks, and **{ledger.unresolved_count}** remain UNRESOLVED.\n"
        )

        md.append("| Metric | Value |")
        md.append("| :--- | :--- |")
        md.append(f"| **Deterministic Verification Rate** | `{v_rate}%` |")
        md.append(f"| **Verified Claims** | `{ledger.verified_count}` |")
        md.append(f"| **Supported Claims** | `{ledger.supported_count}` |")
        md.append(f"| **Failed Claims** | `{ledger.failed_count}` |")
        md.append(f"| **Unresolved Claims / Risks** | `{ledger.unresolved_count}` |")
        md.append(f"| **Not-Run Claims** | `{ledger.not_run_count}` |\n")

        md.append("## Model Routing & Telemetry\n")
        if run.routing_history:
            md.append("| Tier | Model ID | Trigger | Latency | Tokens | Est. Cost |")
            md.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
            for r in run.routing_history:
                md.append(
                    f"| `{r.tier.value}` | `{r.model_id}` | `{r.trigger}` | "
                    f"`{r.latency_ms}ms` | `{r.total_tokens}` | `${r.estimated_cost_usd or 0:.5f}` |"
                )
            md.append("")
        else:
            md.append("No routing decisions recorded.\n")

        md.append("## Verification Ledger\n")
        for claim in ledger.claims:
            icon = {
                ClaimStatus.VERIFIED: "✅ VERIFIED",
                ClaimStatus.SUPPORTED: "📘 SUPPORTED",
                ClaimStatus.FAILED: "❌ FAILED",
                ClaimStatus.UNRESOLVED: "⚠️ UNRESOLVED",
                ClaimStatus.NOT_RUN: "⚪ NOT RUN",
            }.get(claim.status, str(claim.status.value))

            md.append(f"### {claim.claim_id}: {claim.title}")
            md.append(f"- **Status**: `{icon}`")
            md.append(f"- **Category**: `{claim.category.value}`")
            md.append(f"- **Description**: {claim.description}")
            if claim.file_refs:
                md.append(f"- **Files**: `{', '.join(claim.file_refs)}`")
            if claim.evidence_ids:
                md.append(f"- **Backing Evidence IDs**: `{', '.join(claim.evidence_ids)}`")
            if claim.limitations:
                md.append("- **Explicit Limitations**:")
                for lim in claim.limitations:
                    md.append(f"  - *{lim}*")
            if claim.unresolved_questions:
                md.append("- **Unresolved Questions / Risks**:")
                for uq in claim.unresolved_questions:
                    md.append(f"  - {uq}")
            md.append("")

        md.append("## Evidence Records\n")
        for ev in ledger.evidence:
            md.append(f"#### Evidence `{ev.evidence_id}` (Claim `{ev.claim_id}`)")
            md.append(f"- **Check Type**: `{ev.check_type}`")
            md.append(f"- **Result Status**: `{ev.status.value}`")
            if ev.command:
                md.append(f"- **Command**: `{ev.command}`")
            if ev.exit_code is not None:
                md.append(f"- **Exit Code**: `{ev.exit_code}`")
            md.append(f"- **Duration**: `{ev.duration_ms}ms`")
            if ev.stdout:
                md.append(f"- **Stdout**:\n```text\n{ev.stdout}\n```")
            if ev.stderr:
                md.append(f"- **Stderr**:\n```text\n{ev.stderr}\n```")
            md.append("")

        md.append("## Unified Diff\n")
        if run.unified_diff:
            md.append("```diff")
            md.append(run.unified_diff)
            md.append("```\n")
        else:
            md.append("*No files modified or diff not recorded.*\n")

        md.append("## Integrity & Limitations Disclaimer\n")
        md.append(
            "> **Disclaimer**: Automated verification establishes that specific deterministic checks (AST syntax, "
            "isolated imports, and test suites) executed with the recorded outcomes. It does NOT guarantee universal "
            "absence of bugs, absolute security, or that all domain edge cases are covered. VERIQ does not promise "
            "zero hallucination; it guarantees transparent, inspectable evidence for every engineering claim."
        )

        return "\n".join(md)

    @staticmethod
    def generate_json_report(run: RunResponse, ledger: VerificationLedgerSummary) -> Dict[str, Any]:
        """Generates a structured JSON audit artifact."""
        return {
            "veriq_version": "1.0.0",
            "tagline": "Code is generated. Proof is earned.",
            "run": run.model_dump(),
            "ledger": ledger.model_dump(),
        }


report_generator = ReportGenerator()
