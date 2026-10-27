import pytest

from rig.budget import Budget
from rig.exceptions import BudgetExceededError


def test_check_raises_once_max_steps_reached() -> None:
    budget = Budget(
        max_steps=2,
        max_input_tokens=1_000_000,
        max_output_tokens=100_000,
        max_usd=10.0,
        max_wall_clock_s=60,
    )
    budget.steps = 2
    with pytest.raises(BudgetExceededError) as exc_info:
        budget.check()
    assert exc_info.value.status == "steps.exceeded"
