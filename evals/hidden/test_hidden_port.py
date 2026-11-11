import click
import pytest
from click.testing import CliRunner


def run(*args):
    """Invoke a one-option command; built per test so a missing click.Port fails each test."""

    @click.command()
    @click.option("--port", type=click.Port(), default=8000, show_default=True)
    def serve(port):
        click.echo(f"port={port!r}")

    return CliRunner().invoke(serve, list(args))


@pytest.mark.parametrize(("arg", "expected"), [("1", 1), ("8080", 8080), ("65535", 65535)])
def test_ports_in_range_become_ints(arg, expected):
    result = run("--port", arg)
    assert result.exit_code == 0, result.output
    assert result.output == f"port={expected!r}\n"


@pytest.mark.parametrize("arg", ["0", "65536", "-1", "http"])
def test_out_of_range_or_non_numeric_ports_are_usage_errors(arg):
    result = run("--port", arg)
    assert result.exit_code == 2  # a usage error, not a crash
    assert "Invalid value for '--port'" in result.output


def test_help_shows_the_range():
    result = run("--help")
    assert "1<=x<=65535" in result.output
