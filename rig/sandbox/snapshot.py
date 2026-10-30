import subprocess
from pathlib import Path


def create_snapshot(
    source_repo: Path, ref: str, dest: Path, seed_patch: Path | None = None
) -> Path:
    """Populate `dest` with a fresh, history-free checkout of `source_repo` at `ref`.

    If `seed_patch` is given, it is applied to the plain files before any git history
    exists, so the resulting single-commit repo cannot reveal the seeded bug via
    `git log -p` or `git show`.
    """
    dest.mkdir(parents=True)

    archive = subprocess.run(
        ["git", "-C", str(source_repo), "archive", ref], capture_output=True, check=True
    )
    subprocess.run(["tar", "-x", "-C", str(dest)], input=archive.stdout, check=True)

    if seed_patch is not None:
        subprocess.run(["git", "apply", str(seed_patch.resolve())], cwd=dest, check=True)

    subprocess.run(["git", "init", "-q"], cwd=dest, check=True)
    subprocess.run(["git", "add", "-A"], cwd=dest, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=rig",
            "-c",
            "user.email=rig@localhost",
            "commit",
            "-q",
            "-m",
            "snapshot",
        ],
        cwd=dest,
        check=True,
    )
    return dest
