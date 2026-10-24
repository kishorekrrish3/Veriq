"""Standalone Reproducible Benchmark Runner for VERIQ.
Executes the standardized 5-task benchmark comparing single-model baseline
vs. evidence-driven routing with bounded repair.
"""

import sys
import io
import asyncio
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.storage.database import init_database
from app.api.benchmarks import run_benchmarks


async def main():
    print("=" * 75)
    print("VERIQ - Reproducible Benchmark Harness")
    print("Single-Model Baseline vs. Evidence-Driven Routing with Bounded Repair")
    print("=" * 75)

    init_database()
    comparison = await run_benchmarks()

    print(f"\nBenchmark Run ID: {comparison.benchmark_id}")
    print(f"Timestamp:        {comparison.created_at}")
    print(f"Total Tasks:      {comparison.task_count}")
    print("-" * 75)

    # Format table
    header = f"{'Task ID':<10} {'Task Name':<32} {'Base':<8} {'Base Lat':<10} {'Routed':<8} {'Tier':<10} {'Repair':<8}"
    print(header)
    print("-" * 75)

    for t in comparison.tasks:
        base_status = "PASS" if t.baseline_passed else "FAIL"
        routed_status = "PASS" if t.routed_passed else "FAIL"
        repair_str = "YES" if t.repair_triggered else "NO"
        line = f"{t.task_id:<10} {t.task_name:<32} {base_status:<8} {t.baseline_latency_ms:<10.0f} {routed_status:<8} {t.routed_tier_used:<10} {repair_str:<8}"
        print(line)

    print("-" * 75)
    print(f"Baseline Pass Rate:       {comparison.baseline_pass_rate}%")
    print(f"VERIQ Routed Pass Rate:   {comparison.routed_pass_rate}%")
    print(f"Baseline Avg Latency:     {comparison.baseline_avg_latency_ms} ms")
    print(f"Routed Avg Latency:       {comparison.routed_avg_latency_ms} ms")
    print(f"Baseline Total Tokens:    {comparison.baseline_total_tokens}")
    print(f"Routed Total Tokens:      {comparison.routed_total_tokens}")
    print("-" * 75)

    print("\nEmpirical Findings & Conclusions:")
    for c in comparison.conclusions:
        print(f"  • {c}")

    print("=" * 75)


if __name__ == "__main__":
    asyncio.run(main())
