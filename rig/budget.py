import time
from dataclasses import dataclass, field

from .costs.cost_provider import price
from .exceptions import BudgetExceededError


@dataclass
class Budget:
    max_steps: int
    max_input_tokens: int
    max_output_tokens: int
    max_usd: float
    max_wall_clock_s: float

    input_tokens: int = field(init=False, default=0)
    usd: float = field(init=False, default=0)
    output_tokens: int = field(init=False, default=0)
    steps: int = field(init=False, default=0)
    started: float = field(default_factory=time.monotonic)

    def check(self) -> None:
        if self.steps >= self.max_steps:
            raise BudgetExceededError(
                status="steps.exceeded",
                message=f"Maximum steps exceeded. steps_already_ran={self.steps}, "
                f"max_allowed={self.max_steps}",
            )
        if self.input_tokens >= self.max_input_tokens:
            raise BudgetExceededError(
                status="input_tokens.exceeded", message="Maximum input tokens exceeded"
            )
        if self.output_tokens >= self.max_output_tokens:
            raise BudgetExceededError(
                status="output_tokens.exceeded", message="Maximum output tokens exceeded"
            )

        if self.usd >= self.max_usd:
            raise BudgetExceededError(status="usd.exceeded", message="Maximum USD exceeded")
        if time.monotonic() - self.started >= self.max_wall_clock_s:
            raise BudgetExceededError(
                status="wall_time.exceeded", message="Maximum wall clock time exceeded"
            )

    def charge(self, model: str, usage: dict[str, int]) -> None:
        self.steps += 1
        self.input_tokens += usage["input_tokens"]
        self.output_tokens += usage["output_tokens"]
        self.usd += price(model, usage)

    def totals(self) -> dict[str, int | float]:
        return {
            "steps": self.steps,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "usd": round(self.usd, 4),
            "wall_clock_s": round(time.monotonic() - self.started, 4),
        }

    @staticmethod
    def get_dummy_budget() -> Budget:
        return Budget(
            max_steps=100,
            max_input_tokens=1000000,
            max_output_tokens=100000,
            max_usd=0.5,
            max_wall_clock_s=300,
        )
