import click
from click.testing import CliRunner


def run(*args):
    @click.group()
    def cli():
        pass

    @cli.command(aliases=["rm", "del"])
    @click.argument("name")
    def remove(name):
        """Remove an item."""
        click.echo(f"removed {name}")

    @cli.command()
    def list():
        """List items."""
        click.echo("listed")

    return CliRunner().invoke(cli, [*args])


def test_each_alias_runs_the_command():
    for name in ("remove", "rm", "del"):
        result = run(name, "x")
        assert result.exit_code == 0, result.output
        assert result.output == "removed x\n"


def test_commands_without_aliases_are_unchanged():
    assert run("list").output == "listed\n"


def test_help_lists_the_command_once_with_its_aliases():
    result = run("--help")
    rows = [line.strip() for line in result.output.splitlines()]
    assert any(row.startswith("remove (rm, del)") for row in rows), result.output
    assert not any(row.startswith(("rm ", "del ")) for row in rows), result.output


def test_an_unknown_name_is_still_an_error():
    result = run("rn", "x")
    assert result.exit_code == 2
    assert "No such command 'rn'" in result.output
