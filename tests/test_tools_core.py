from rig.tools._core import MAX_OUT, truncate


def test_truncate_leaves_short_output_untouched() -> None:
    s = "ok"
    assert truncate(s) == s


def test_truncate_cuts_long_output_but_keeps_head_and_tail() -> None:
    s = "x" * (MAX_OUT * 5)
    out = truncate(s)
    assert len(out) < len(s)
    assert out.startswith("x")
    assert out.endswith("x")
    assert "characters omitted" in out
