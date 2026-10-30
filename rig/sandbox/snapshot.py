import subprocess
from pathlib import Path


def create_snapshot(
    source_repo: Path, ref: str, dest: Path, seed_patch: Path | None = None
) -> Path:
    """Populate `dest` with a fresh, history-free checkout of `source_repo` at `ref`.

    If `seed_patch` is given, it is applied before the one commit is made, so the resulting
    repo cannot reveal the seeded bug via `git log -p` or `git show`.

    `git init` comes before `git apply` on purpose. Run outside a repository of its own,
    `git apply` works relative to whatever repository encloses `dest` (rig's own, since
    snapshots live under runs/) and silently skips every path outside it while still
    exiting 0. That dropped every seed from Week 1 on; the check after applying makes a
    skipped seed an error instead.
    """
    dest.mkdir(parents=True)

    archive = subprocess.run(
        ["git", "-C", str(source_repo), "archive", ref], capture_output=True, check=True
    )
    subprocess.run(["tar", "-x", "-C", str(dest)], input=archive.stdout, check=True)

    subprocess.run(["git", "init", "-q"], cwd=dest, check=True)
    if seed_patch is not None:
        patch = str(seed_patch.resolve())
        subprocess.run(["git", "apply", patch], cwd=dest, check=True)
        landed = subprocess.run(
            ["git", "apply", "--check", "-R", patch], cwd=dest, capture_output=True
        )
        if landed.returncode != 0:
            raise RuntimeError(f"seed {seed_patch.name} did not apply to the snapshot at {dest}")
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
