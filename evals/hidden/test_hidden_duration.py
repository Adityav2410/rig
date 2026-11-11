from datetime import timedelta

import click
import pytest
from click.testing import CliRunner


def run(*args):
    @click.command()
    @click.option("--timeout", type=click.Duration(), default=timedelta(minutes=5))
    def wait(timeout):
        click.echo(repr(timeout))

    return CliRunner().invoke(wait, list(args))


@pytest.mark.parametrize(
    ("arg", "expected"),
    [
        ("90s", timedelta(seconds=90)),
        ("5m", timedelta(minutes=5)),
        ("2h", timedelta(hours=2)),
        ("1d", timedelta(days=1)),
        ("1h30m", timedelta(hours=1, minutes=30)),
        ("1d2h3m4s", timedelta(days=1, hours=2, minutes=3, seconds=4)),
        ("45", timedelta(seconds=45)),  # a bare number is seconds
    ],
)
def test_durations_become_timedeltas(arg, expected):
    result = run("--timeout", arg)
    assert result.exit_code == 0, result.output
    assert result.output == f"{expected!r}\n"


def test_a_timedelta_default_passes_through():
    assert run().output == f"{timedelta(minutes=5)!r}\n"


@pytest.mark.parametrize("arg", ["", "1x", "h", "5m1h", "-5m", "1.5h"])
def test_malformed_durations_are_usage_errors(arg):
    result = run("--timeout", arg)
    assert result.exit_code == 2  # a usage error, not a crash
    assert "Invalid value for '--timeout'" in result.output


def test_help_names_the_type():
    assert "--timeout DURATION" in run("--help").output
