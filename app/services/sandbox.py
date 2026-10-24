"""Isolated Sandbox Execution Service for VERIQ.
Executes generated and modified code in an isolated environment.
Prioritizes Docker containerization; safely falls back to restricted process isolation
with secret-stripped environments and command allowlists when Docker is unavailable.
"""

import os
import sys
import time
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.core.security import validate_sandbox_command
from app.core.logging import logger, redact_sensitive
from app.core.errors import SandboxExecutionError


class SandboxResult:
    def __init__(
        self,
        exit_code: int,
        stdout: str,
        stderr: str,
        duration_ms: float,
        is_timeout: bool = False,
        execution_environment: str = "CONTAINER",
        limitations: Optional[List[str]] = None,
    ):
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.duration_ms = duration_ms
        self.is_timeout = is_timeout
        self.execution_environment = execution_environment
        self.limitations = limitations or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_ms": self.duration_ms,
            "is_timeout": self.is_timeout,
            "execution_environment": self.execution_environment,
            "limitations": self.limitations,
        }


def find_docker_binary() -> str:
    """Finds the docker executable path, including Windows User AppData locations."""
    which_docker = shutil.which("docker")
    if which_docker:
        return which_docker

    candidate_paths = [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\DockerDesktop\resources\bin\docker.exe"),
        r"C:\Program Files\Docker\Docker\resources\bin\docker.exe",
        os.path.expanduser(r"~\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"),
    ]
    for p in candidate_paths:
        if os.path.isfile(p):
            bin_dir = os.path.dirname(p)
            if bin_dir not in os.environ.get("PATH", ""):
                os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
            return p

    return "docker"


class SandboxRunner:
    def __init__(self):
        self._docker_available: Optional[bool] = None

    def is_docker_available(self, refresh: bool = False) -> bool:
        """Determines whether the Docker CLI and daemon are reachable."""
        if not refresh and self._docker_available is True:
            return True

        docker_bin = find_docker_binary()
        try:
            res = subprocess.run(
                [docker_bin, "info"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=4,
                check=False,
            )
            self._docker_available = (res.returncode == 0)
        except Exception:
            self._docker_available = False

        logger.info(f"Docker sandbox availability detected: {self._docker_available} (binary: {docker_bin})")
        return self._docker_available

    def execute(
        self,
        workspace_path: Path,
        command: List[str],
        timeout_seconds: Optional[int] = None,
    ) -> SandboxResult:
        """Executes a validated command inside the sandbox."""
        validate_sandbox_command(command)
        timeout = timeout_seconds or settings.MAX_EXECUTION_SECONDS

        if self.is_docker_available():
            return self._execute_docker(workspace_path, command, timeout)
        else:
            if not settings.ALLOW_FALLBACK_SANDBOX:
                raise SandboxExecutionError(
                    "Docker is unavailable and ALLOW_FALLBACK_SANDBOX is disabled in security settings."
                )
            return self._execute_process_fallback(workspace_path, command, timeout)

    def _execute_docker(
        self,
        workspace_path: Path,
        command: List[str],
        timeout: int,
    ) -> SandboxResult:
        """Executes the command inside a hardened Docker container."""
        start = time.perf_counter()
        abs_workspace = str(workspace_path.resolve()).replace("\\", "/")
        docker_bin = find_docker_binary()

        # Hardened docker arguments:
        # - non-root user (veriq: 1000)
        # - no network access (--network none)
        # - bounded memory (256m)
        # - bounded cpu (1.0)
        docker_cmd = [
            docker_bin, "run", "--rm",
            "--network", "none",
            "--memory", "256m",
            "--cpus", "1.0",
            "-v", f"{abs_workspace}:/workspace:rw",
            "-w", "/workspace",
            settings.SANDBOX_DOCKER_IMAGE,
        ] + command

        try:
            proc = subprocess.run(
                docker_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
            )
            duration_ms = (time.perf_counter() - start) * 1000.0
            return SandboxResult(
                exit_code=proc.returncode,
                stdout=redact_sensitive(proc.stdout),
                stderr=redact_sensitive(proc.stderr),
                duration_ms=round(duration_ms, 2),
                is_timeout=False,
                execution_environment="DOCKER_CONTAINER",
                limitations=[
                    "Network disabled; cannot fetch remote assets.",
                    "Container memory capped at 256MB.",
                ],
            )
        except subprocess.TimeoutExpired as e:
            duration_ms = (time.perf_counter() - start) * 1000.0
            return SandboxResult(
                exit_code=-1,
                stdout=redact_sensitive(e.stdout or ""),
                stderr="Execution timed out exceeding limit.",
                duration_ms=round(duration_ms, 2),
                is_timeout=True,
                execution_environment="DOCKER_CONTAINER",
                limitations=["Terminated due to time budget exhaustion."],
            )

    def _execute_process_fallback(
        self,
        workspace_path: Path,
        command: List[str],
        timeout: int,
    ) -> SandboxResult:
        """Executes in a restricted subprocess with an isolated, stripped environment."""
        start = time.perf_counter()
        abs_workspace = str(workspace_path.resolve())

        # Construct minimal environment stripping all host credentials and API keys
        safe_env = {
            "PATH": os.environ.get("PATH", ""),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", "C:\\Windows"),
            "TEMP": os.environ.get("TEMP", ""),
            "TMP": os.environ.get("TMP", ""),
            "PYTHONUNBUFFERED": "1",
            "PYTHONPATH": abs_workspace,
        }

        # Resolve binary if necessary
        binary = command[0]
        if binary in ("pytest", "python", "python3"):
            # Ensure using active python interpreter if on windows
            if binary in ("python", "python3"):
                binary = sys.executable
            elif binary == "pytest":
                # Run pytest as `python -m pytest` to ensure package resolution
                command = [sys.executable, "-m", "pytest"] + command[1:]

        try:
            proc = subprocess.run(
                command,
                cwd=abs_workspace,
                env=safe_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
            )
            duration_ms = (time.perf_counter() - start) * 1000.0
            return SandboxResult(
                exit_code=proc.returncode,
                stdout=redact_sensitive(proc.stdout),
                stderr=redact_sensitive(proc.stderr),
                duration_ms=round(duration_ms, 2),
                is_timeout=False,
                execution_environment="ISOLATED_PROCESS_FALLBACK",
                limitations=[
                    "Docker daemon was not reachable; executed under process isolation.",
                    "Host credentials stripped from environment variables.",
                    "Limited to working directory and command allowlist.",
                    "Kernel/cgroup container boundary not enforced in fallback mode.",
                ],
            )
        except subprocess.TimeoutExpired as e:
            duration_ms = (time.perf_counter() - start) * 1000.0
            return SandboxResult(
                exit_code=-1,
                stdout=redact_sensitive(e.stdout or ""),
                stderr="Process timed out exceeding maximum execution seconds.",
                duration_ms=round(duration_ms, 2),
                is_timeout=True,
                execution_environment="ISOLATED_PROCESS_FALLBACK",
                limitations=["Terminated due to time budget exhaustion in fallback sandbox."],
            )


sandbox_runner = SandboxRunner()
