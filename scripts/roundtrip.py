import json
import os

import httpx


def count_lines(filepath: str) -> int:
    """Count the number of lines in a file."""
    with open(filepath) as file:
        return sum(1 for _ in file)


ANTHROPIC_MESSAGES_ENDPOINT = "https://api.anthropic.com/v1/messages"

FILEPATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../AGENTS.md"))  # noqa

MESSAGES = []

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

_DEFAULT_REQUEST_PAYLOAD = {
    "max_tokens": 1000,
    "messages": MESSAGES,
    "model": "claude-haiku-5-5",
    "tools": TOOLS,
}

REQUEST_PAYLOAD = {
    "max_tokens": 1000,
    "messages": MESSAGES,
    "model": "claude-haiku-5-5",
    "tools": TOOLS,
}


def call_anthropic_api():
    r = httpx.post(
        url=ANTHROPIC_MESSAGES_ENDPOINT,
        headers={
            "Content-Type": "application/json",
            "x-api-key": os.environ.get("ANTHROPIC_API_KEY"),
            "anthropic-version": "2023-06-01",
        },
        json=_DEFAULT_REQUEST_PAYLOAD,
    )

    print(
        f"Request sent to {ANTHROPIC_MESSAGES_ENDPOINT} with payload: "
        f"{json.dumps(_DEFAULT_REQUEST_PAYLOAD, indent=4)}"
    )

    if r.status_code != 200:
        raise ValueError(f"Error: {r.status_code} - {r.text}")

    print(f"\n\nResponse received: {json.dumps(r.json(), indent=4)}\n\n")

    MESSAGES.append({"role": "assistant", "content": r.json()["content"]})

    return r.json()


def handle_file_line_counter_tool_use(tool_use_block):
    tool_input = tool_use_block["input"]
    file_path = tool_input.get("file_path")
    if file_path:
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
    else:
        print("No file path provided for line counting.")


def process_tool_use(content_blocks):
    for block in content_blocks:
        if block["type"] != "tool_use":
            continue

    if block["name"] == "file_line_counter":
        handle_file_line_counter_tool_use(block)
    else:
        raise ValueError(f"Unhandled tool: {block['name']}")


MESSAGES.append({"role": "user", "content": "Count number of lines in file " + FILEPATH})

### Call the API and process the response
response_payload = call_anthropic_api()
if response_payload["stop_reason"] != "tool_use":
    print("No tool use detected in the response.")
    exit(1)

# Tool use detected, process it
process_tool_use(response_payload["content"])
# send response with tool results back to the API

# del _DEFAULT_REQUEST_PAYLOAD["tools"]

response_payload = call_anthropic_api()

# Print the final response from the API
print(f"Final response from API: {json.dumps(response_payload, indent=4)}")
if response_payload["stop_reason"] == "end_turn":
    print("Conversation ended successfully.")
    print(f"Final content: {response_payload['content']}")
