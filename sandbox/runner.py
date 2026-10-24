"""Standalone Deterministic Verification Runner for Sandbox Environments.
Executes requested test and syntax commands, capturing structured JSON telemetry.
"""

import sys
import json
import time
import subprocess
from pathlib import Path


def run_command(command: list[str], cwd: Path) -> dict:
    start = time.perf_counter()
    try:
        proc = subprocess.run(
            command,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        duration = (time.perf_counter() - start) * 1000.0
        return {
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "duration_ms": round(duration, 2),
            "timeout": False,
        }
    except subprocess.TimeoutExpired as e:
        duration = (time.perf_counter() - start) * 1000.0
        return {
            "exit_code": -1,
            "stdout": e.stdout or "",
            "stderr": "Execution timed out",
            "duration_ms": round(duration, 2),
            "timeout": True,
        }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No command specified"}))
        sys.exit(1)

    command = sys.argv[1:]
    workspace = Path("/workspace") if Path("/workspace").exists() else Path.cwd()
    res = run_command(command, workspace)
    print(json.dumps(res))
    sys.exit(res["exit_code"] if res["exit_code"] >= 0 else 1)


if __name__ == "__main__":
    main()
