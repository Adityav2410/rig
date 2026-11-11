import click
from click.testing import CliRunner


def run(*args):
    @click.command()
    @click.option("--color", type=click.Choice(["red", "green", "blue"]))
    @click.argument("mode", type=click.Choice(["start", "stop"]), required=False)
    def paint(color, mode):
        click.echo(f"{color} {mode}")

    return CliRunner().invoke(paint, list(args))


def test_a_typo_suggests_the_closest_choice():
    result = run("--color", "gren")
    assert result.exit_code == 2
    assert "'gren' is not one of 'red', 'green', 'blue'." in result.output  # message kept
    assert "Did you mean 'green'?" in result.output


def test_arguments_get_suggestions_too():
    result = run("stpo")
    assert result.exit_code == 2
    assert "Did you mean 'stop'?" in result.output


def test_nothing_close_means_no_suggestion():
    result = run("--color", "purple")
    assert result.exit_code == 2
    assert "'purple' is not one of" in result.output
    assert "Did you mean" not in result.output


def test_valid_choices_still_work():
    result = run("--color", "green", "start")
    assert result.exit_code == 0
    assert result.output == "green start\n"
