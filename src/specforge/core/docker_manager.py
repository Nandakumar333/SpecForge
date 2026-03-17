"""DockerManager — build, health-check, and compose operations for services."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

import yaml

from specforge.core.result import Err, Ok, Result


class DockerManager:
    """Manage Docker lifecycle for a single service."""

    def __init__(self, project_root: Path, service_slug: str) -> None:
        self._root = project_root
        self._slug = service_slug

    # ── build ────────────────────────────────────────────────────────

    def build_image(self) -> Result[str, str]:
        """Build Docker image. Returns Ok(image_tag) or Err."""
        dockerfile = self._root / "src" / self._slug / "Dockerfile"
        if not dockerfile.exists():
            return Err(f"Dockerfile not found: {dockerfile}")

        tag = f"{self._slug}:latest"
        cmd = ["docker", "build", "-t", tag, "-f", str(dockerfile), str(self._root)]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
            return Err(f"docker build failed: {exc}")

        if proc.returncode != 0:
            return Err(proc.stderr.strip() or "docker build failed")
        return Ok(tag)

    # ── health check ─────────────────────────────────────────────────

    def health_check(self, timeout: int = 30) -> Result[bool, str]:
        """Run container and poll /health endpoint."""
        container = f"{self._slug}-healthcheck"
        tag = f"{self._slug}:latest"

        # Start container
        run_cmd = [
            "docker", "run", "-d", "--name", container, "-p", "8080:8080", tag,
        ]
        try:
            proc = subprocess.run(run_cmd, capture_output=True, text=True, timeout=30)
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
            return Err(f"docker run failed: {exc}")

        if proc.returncode != 0:
            return Err(proc.stderr.strip() or "docker run failed")

        # Poll health endpoint
        healthy = False
        for _ in range(timeout):
            curl = subprocess.run(
                ["curl", "-sf", "http://localhost:8080/health"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if curl.returncode == 0:
                healthy = True
                break
            time.sleep(1)

        # Cleanup
        subprocess.run(
            ["docker", "stop", container], capture_output=True, text=True, timeout=15,
        )
        subprocess.run(
            ["docker", "rm", container], capture_output=True, text=True, timeout=15,
        )

        if not healthy:
            return Err(f"Health check timeout after {timeout}s")
        return Ok(True)

    # ── contract tests ───────────────────────────────────────────────

    def run_contract_tests(self) -> Result[bool, str]:
        """Run pytest on contract test directory."""
        test_dir = str(self._root / "tests" / self._slug / "contract")
        cmd = ["pytest", test_dir, "-v"]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
            return Err(f"Contract tests failed: {exc}")

        if proc.returncode != 0:
            err = (
                proc.stderr.strip()
                or proc.stdout.strip()
                or "contract tests failed"
            )
            return Err(err)
        return Ok(True)

    # ── docker-compose registration ──────────────────────────────────

    def register_in_compose(
        self, compose_path: Path | None = None,
    ) -> Result[bool, str]:
        """Add service to docker-compose.yml."""
        path = compose_path or self._root / "docker-compose.yml"

        if path.exists():
            try:
                data = yaml.safe_load(path.read_text()) or {}
            except yaml.YAMLError as exc:
                return Err(f"Invalid YAML: {exc}")
        else:
            data = {}

        services = data.setdefault("services", {})
        services[self._slug] = {
            "image": f"{self._slug}:latest",
            "build": {"context": ".", "dockerfile": f"src/{self._slug}/Dockerfile"},
            "profiles": ["test"],
        }

        tmp = path.with_suffix(".yml.tmp")
        try:
            tmp.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
            tmp.replace(path)
        except OSError as exc:
            return Err(f"Failed to write compose file: {exc}")

        return Ok(True)

    # ── compose profiles ─────────────────────────────────────────────

    def compose_up_test_profile(self) -> Result[bool, str]:
        """Start test profile containers."""
        cmd = ["docker-compose", "--profile", "test", "up", "-d"]
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120, cwd=str(self._root),
            )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
            return Err(f"compose up failed: {exc}")

        if proc.returncode != 0:
            return Err(proc.stderr.strip() or "compose up failed")
        return Ok(True)

    def compose_down_test_profile(self) -> Result[bool, str]:
        """Stop test profile containers."""
        cmd = ["docker-compose", "--profile", "test", "down"]
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60, cwd=str(self._root),
            )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
            return Err(f"compose down failed: {exc}")

        if proc.returncode != 0:
            return Err(proc.stderr.strip() or "compose down failed")
        return Ok(True)
