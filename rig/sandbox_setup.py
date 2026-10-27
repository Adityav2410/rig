import shutil
import subprocess
from pathlib import Path

from .exceptions import SandboxUnavailable
from .logging import get_logger

logger = get_logger()

IMAGE_NAME = "rig-sandbox:v0.1"
DOCKERFILE = "docker/Dockerfile.sandbox"


def ensure_sandbox_ready() -> None:
    if not docker_binary_exists():
        raise SandboxUnavailable(
            "Docker is required to run rig safely (sandboxed bash/search). "
            "Install it from https://docs.docker.com/get-docker/ and re-run."
        )
    if not docker_daemon_responding():
        raise SandboxUnavailable("Docker is installed but not running — start it and re-run.")
    if image_exists(IMAGE_NAME):
        logger.info(f"{IMAGE_NAME} already exists. Nothing to build.")
    else:
        logger.info(f"{IMAGE_NAME} not found, building from {DOCKERFILE} (one-time, ~1-2 min)...")
        result = subprocess.run(
            ["docker", "build", "-t", IMAGE_NAME, "-f", DOCKERFILE, "."], cwd=Path(__file__).parent
        )
        if result.returncode != 0:
            raise SandboxUnavailable(f"image build failed: {result.stderr!r}")


def docker_binary_exists() -> bool:
    return shutil.which("docker") is not None


def docker_daemon_responding() -> bool:
    return subprocess.run(["docker", "info"], capture_output=True).returncode == 0


def image_exists(name: str) -> bool:
    out = subprocess.run(["docker", "images", "-q", name], capture_output=True)
    return out.stdout.strip() != b""
