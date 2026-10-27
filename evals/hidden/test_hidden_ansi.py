import click
from click.formatting import measure_table


def test_measure_table_ignores_ansi():
    assert measure_table([(click.style("--x", fg="red"), "help")])[0] == 3
