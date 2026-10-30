"""Week 1, Monday: one tool call by hand over raw HTTP, before rig has any modules.

The model is asked to count the lines of AGENTS.md, calls the `file_line_counter` tool, gets
the result back, and answers. Needs ANTHROPIC_API_KEY; makes two billable requests.
"""

import json
import os
from typing import Any

import httpx

ANTHROPIC_MESSAGES_ENDPOINT = "https://api.anthropic.com/v1/messages"

FILEPATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../AGENTS.md"))

MESSAGES: list[dict[str, Any]] = []

TOOLS = [
    {
        "name": "file_line_counter",
        "description": "Counts the number of lines in a specified file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path to the file for which to count the number of lines.",
                }
            },
            "required": ["file_path"],
        },
        "input_examples": [{"file_path": "rig/notes/wire/01-request.json"}],
    }
]

REQUEST_PAYLOAD: dict[str, Any] = {
    "max_tokens": 1000,
    "messages": MESSAGES,
    "model": "claude-haiku-5-5",
    "tools": TOOLS,
}


def count_lines(filepath: str) -> int:
    """Count the number of lines in a file."""
    with open(filepath) as file:
        return sum(1 for _ in file)


def call_anthropic_api() -> dict[str, Any]:
    r = httpx.post(
        url=ANTHROPIC_MESSAGES_ENDPOINT,
        headers={
            "Content-Type": "application/json",
            "x-api-key": os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
        },
        json=REQUEST_PAYLOAD,
    )

    print(
        f"Request sent to {ANTHROPIC_MESSAGES_ENDPOINT} with payload: "
        f"{json.dumps(REQUEST_PAYLOAD, indent=4)}"
    )

    if r.status_code != 200:
        raise ValueError(f"Error: {r.status_code} - {r.text}")

    body: dict[str, Any] = r.json()
    print(f"\n\nResponse received: {json.dumps(body, indent=4)}\n\n")
    MESSAGES.append({"role": "assistant", "content": body["content"]})
    return body


def handle_file_line_counter_tool_use(tool_use_block: dict[str, Any]) -> None:
    file_path = tool_use_block["input"].get("file_path")
    if not file_path:
        print("No file path provided for line counting.")
        return
    line_count = count_lines(file_path)
    print(f"Number of lines in file '{file_path}': {line_count}")
    MESSAGES.append(
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_block["id"],
                    "content": f"{line_count}",
                }
            ],
        }
    )


def process_tool_use(content_blocks: list[dict[str, Any]]) -> None:
    for block in content_blocks:
        if block["type"] != "tool_use":
            continue
        if block["name"] == "file_line_counter":
            handle_file_line_counter_tool_use(block)
        else:
            raise ValueError(f"Unhandled tool: {block['name']}")


def main() -> None:
    MESSAGES.append({"role": "user", "content": "Count number of lines in file " + FILEPATH})

    response_payload = call_anthropic_api()
    if response_payload["stop_reason"] != "tool_use":
        print("No tool use detected in the response.")
        raise SystemExit(1)

    process_tool_use(response_payload["content"])  # appends the tool results
    response_payload = call_anthropic_api()  # send them back

    print(f"Final response from API: {json.dumps(response_payload, indent=4)}")
    if response_payload["stop_reason"] == "end_turn":
        print("Conversation ended successfully.")
        print(f"Final content: {response_payload['content']}")


if __name__ == "__main__":
    main()
