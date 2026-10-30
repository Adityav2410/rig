"""When the raw client retries: the API's x-should-retry wins, otherwise the status decides."""

import httpx
import pytest

from rig.core.llm import _should_retry


@pytest.mark.parametrize(
    ("status", "hint", "retry"),
    [
        (429, None, True),  # rate limited, no hint: retry
        (529, None, True),  # overloaded, no hint: retry
        (500, "false", False),  # the API says not to
        (400, None, False),  # a bug in the request
        (400, "true", True),  # the API says to
    ],
)
def test_should_retry(status: int, hint: str | None, retry: bool) -> None:
    headers = {"x-should-retry": hint} if hint else {}
    assert _should_retry(httpx.Response(status, headers=headers)) is retry
