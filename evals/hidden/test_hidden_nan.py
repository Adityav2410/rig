import math

import click
import pytest


@pytest.mark.parametrize(
    "kw", [{"min": 0, "max": 1}, {"min": 0}, {"max": 1}, {"min": 0, "max": 1, "clamp": True}]
)
def test_float_range_rejects_nan(kw):
    with pytest.raises(click.BadParameter):
        click.FloatRange(**kw).convert("nan", None, None)


def test_unbounded_float_still_accepts_nan():
    assert math.isnan(click.FLOAT.convert("nan", None, None))
