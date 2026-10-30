import os
import subprocess
from pathlib import Path
from subprocess import run
from time import sleep

from ..core.exceptions import SandboxError
from ..util.logging import get_logger
from .setup import IMAGE_NAME

logger = get_logger()

_DOCKER_FLAGS = {
    "cpus": "2",
    "memory": "2g",
    "network": "none",
    "pids-limit": "256",
    "cap-drop": "ALL",
    "security-opt": "no-new-privileges=true",
}


class Workspace:
    def __init__(self, root: Path, name: str, run_id: str, use_sandbox: bool) -> None:
        self.root = root
        self.name = name
        self._run_id = run_id
        self._container_name = f"rig-{self._run_id}"
        self._use_sandbox = use_sandbox
        self._exec_prefix: list[str] = (
            ["docker", "exec", "-w", "/repo", self._container_name] if use_sandbox else []
        )
        self._started = False

    def _launch_docker_container(self) -> None:
        _cmd = [
            "docker",
            "run",
            "-d",
            "--name",
            self._container_name,
        ]
        for k, v in _DOCKER_FLAGS.items():
            _cmd.extend([f"--{k}", v])
        _cmd += [
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "-v",
            f"{self.root}:/repo",
            IMAGE_NAME,
            "sleep",
            "infinity",
        ]
        logger.debug(f"Launching docker comtainer with command: \n{_cmd}")

        result = subprocess.run(_cmd, capture_output=True)
        if result.returncode != 0:
            raise SandboxError(f"docker run failed: {result.stderr!r}")

    def _verify_running(self) -> None:
        # poll briefly rather than trusting `docker run -d`'s exit code alone —
        # the container can be created and then immediately exit (bad image,
        # bad mount) and `docker run -d` still returns 0
        N = 5
        short_delay = 2
        for _ in range(N):
            state = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}}", self._container_name],
                capture_output=True,
            )
            if state.stdout.strip().decode() == "true":
                return
            sleep(short_delay)
        logs = run(["docker", "logs", self._container_name], capture_output=True)
        raise SandboxError(f"container never reached Running: {logs}")

    def start(self) -> None:
        if not self._use_sandbox:
            return
        if self._started:
            return

        self._launch_docker_container()
        self._verify_running()
        # verify container is offline
        run(
            self._exec_prefix
            + ["pip", "install", "-q", "--no-deps", "--no-build-isolation", "-e", "/repo"],
            capture_output=True,
        )
        self._started = True

    def stop(self) -> None:
        if not self._started:
            return
        _ = run(["docker", "rm", "-f", self._container_name], capture_output=True)
        self._verify_removed()

    def _verify_removed(self) -> None:
        check = run(
            ["docker", "ps", "-a", "-q", "-f", f"name=^{self._container_name}$"],
            capture_output=True,
        )
        if check.stdout.strip().decode() == "":
            self._started = False
        else:
            logger.warning(f"{self._container_name} still present after rm -f")

    @property
    def exec_prefix(self) -> list[str]:
        if self._use_sandbox and not self._started:
            raise SandboxError(
                f"Sandbox is not started. Cannot access exec_prefix. "
                f"First run {self.__class__.__name__}.start() before accessing "
                f"{self.__class__.__name__}.exec_prefix"
            )
        return self._exec_prefix

    def __enter__(self) -> Workspace:
        self.start()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.stop()

    @property
    def started(self) -> bool:
        return self._started

    def copy_into(self, host_path: Path, container_path: str) -> None:
        """Copy a host file into the running container, outside the /repo bind mount."""
        if not self._started:
            raise SandboxError("Sandbox is not started. Cannot copy_into before start().")
        parent = container_path.rsplit("/", 1)[0] or "/"
        run(self._exec_prefix + ["mkdir", "-p", parent], capture_output=True)
        run(
            ["docker", "cp", str(host_path), f"{self._container_name}:{container_path}"],
            capture_output=True,
        )

    @staticmethod
    def get_dummy_instance() -> Workspace:
        root = Path(os.getcwd())
        return Workspace(root=root, name=root.name, run_id="dummy", use_sandbox=False)
