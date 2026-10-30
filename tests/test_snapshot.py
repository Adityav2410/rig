import subprocess
from pathlib import Path

from rig.sandbox.snapshot import create_snapshot

CLICK = Path("workspaces/click")


def test_create_snapshot_is_a_single_fresh_commit(tmp_path: Path) -> None:
    dest = tmp_path / "snap"
    create_snapshot(source_repo=CLICK, ref="HEAD", dest=dest)

    assert (dest / "src" / "click" / "core.py").exists()

    log = subprocess.run(
        ["git", "-C", str(dest), "log", "--oneline"], capture_output=True, text=True, check=True
    )
    assert len(log.stdout.strip().splitlines()) == 1


def test_create_snapshot_applies_seed_patch_before_committing(tmp_path: Path) -> None:
    # Build a real seed patch the same way a TXX.patch gets built: make an edit in one
    # snapshot and diff it against its own clean HEAD.
    clean = tmp_path / "clean"
    create_snapshot(source_repo=CLICK, ref="HEAD", dest=clean)
    target = clean / "CHANGES.md"
    target.write_text("seeded-bug-marker\n" + target.read_text())
    patch_text = subprocess.run(
        ["git", "-C", str(clean), "diff"], capture_output=True, text=True, check=True
    ).stdout
    patch_path = tmp_path / "seed.patch"
    patch_path.write_text(patch_text)

    seeded = tmp_path / "seeded"
    create_snapshot(source_repo=CLICK, ref="HEAD", dest=seeded, seed_patch=patch_path)

    assert (seeded / "CHANGES.md").read_text().startswith("seeded-bug-marker")


def test_a_seed_lands_even_when_the_snapshot_is_inside_another_repo(tmp_path: Path) -> None:
    # The eval harness puts snapshots under runs/, inside rig's own repository. A seed must
    # still land there (it was silently dropped before), and T04's real seed is the proof.
    outer = tmp_path / "outer"
    outer.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=outer, check=True)
    seed = Path("evals/seeds/T04.patch").resolve()

    dest = create_snapshot(
        source_repo=CLICK, ref="HEAD", dest=outer / "runs" / "snap", seed_patch=seed
    )

    assert "if total_length >= max_length:" in (dest / "src" / "click" / "utils.py").read_text()
