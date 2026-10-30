import contextlib
import json
import os
import random
import time
from typing import Any

import httpx
from pydantic import BaseModel

from ..util.logging import get_logger
from ..util.timer import Timer
from .exceptions import LLMError

logger = get_logger()

API_URL = "https://api.anthropic.com/v1/messages"
_RETRYABLE_STATUS_CODES = {408, 409, 429, 500, 502, 503, 504, 529}

_API_KEY = None


def set_api_key(api_key: str) -> None:
    global _API_KEY
    _API_KEY = api_key


class ApiCallInfo(BaseModel):
    attempts: int
    latency_s: float
    request_id: str | None = None


def _get_headers() -> dict[str, str]:
    api_key = _API_KEY or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise LLMError(message="No API key set. Call set_api_key() or set ANTHROPIC_API_KEY.")
    return {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }


def _should_retry(response: httpx.Response) -> bool:
    """Retry a retryable status unless the API says not to; retry anything it says to retry.

    `x-should-retry` is the API's own verdict and wins either way. Without it, the status
    decides: a 429 or 5xx is worth retrying, a 400 is a bug in the request.
    """
    hint = response.headers.get("x-should-retry")
    if hint is not None:
        return str(hint) == "true"
    return response.status_code in _RETRYABLE_STATUS_CODES


def call(
    request: dict[str, Any], *, timeout: float = 300, max_retries: int = 3
) -> tuple[dict[str, Any], ApiCallInfo]:
    """
    Call the API with the given request body and return the response.
    """
    last_error = None
    last_status = "connection"  # the cause in error.llm.<cause>: an HTTP status, or "connection"
    timer = Timer()
    wait = None
    _headers = _get_headers()
    for attempt in range(max_retries):
        try:
            timer.restart()
            logger.debug(
                f"Making API call to LLM: \n\n\npayload:----{json.dumps(request, indent=4)}"
            )
            response = httpx.post(url=API_URL, headers=_headers, json=request, timeout=timeout)
            logger.debug(f"\n\n\n API response: {json.dumps(response.json(), indent=4)}")
        except httpx.TransportError as e:
            last_error, last_status = repr(e), "connection"
        else:
            if response.status_code == 200:
                return response.json(), ApiCallInfo(
                    attempts=attempt + 1,
                    latency_s=timer.elapsed_s(),
                    request_id=response.headers.get("x-request-id"),
                )

            last_error = f"Http Error: {response.status_code} - {response.text}"
            last_status = str(response.status_code)
            if not _should_retry(response):
                # API explicitly says to not retry.
                break

            if attempt < max_retries - 1:
                with contextlib.suppress(ValueError):
                    wait = float(response.headers.get("retry-after"))
                # Sleep before retrying
                time.sleep(wait if wait is not None else min(2**attempt + random.uniform(0, 1), 60))

    raise LLMError(
        message=f"Request failed after {attempt + 1} attempts. Last error: {last_error}",
        status=last_status,
    )
