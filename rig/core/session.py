"""An append-only session log: resume and fork without rewriting history (pi's session-manager).

Every entry is one JSON line, `{id, parent_id, type, payload}`, flushed as it is written.
Entries form a tree through `parent_id`: a plain session is a single chain, and a fork is a
new entry whose parent is an earlier one, so the old continuation stays in the file untouched.
"""

import json
import uuid
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from ..providers.types import Message

# dict -> UserMessage | AssistantMessage | ToolResult, picked by the "role" tag
MESSAGE: TypeAdapter[Message] = TypeAdapter(Message)


class SessionLog:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        entries = self.load() if self.path.exists() else []
        # The entry new entries chain to: the end of the file for a resume, or an earlier
        # entry after checkout() for a fork.
        self.head: str | None = entries[-1]["id"] if entries else None

    def append(self, type: str, payload: dict[str, Any], parent_id: str | None = None) -> str:
        """Write one entry under `parent_id` (default: the current head) and make it the head."""
        entry_id = uuid.uuid4().hex[:12]
        entry = {
            "id": entry_id,
            "parent_id": parent_id if parent_id is not None else self.head,
            "type": type,
            "payload": payload,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as f:
            f.write(json.dumps(entry) + "\n")
            f.flush()
        self.head = entry_id
        return entry_id

    def append_message(self, message: Message) -> str:
        return self.append("message", message.model_dump(mode="json"))

    def load(self) -> list[dict[str, Any]]:
        """Every entry in file order. A torn last line (a kill mid-write) is skipped, not fatal."""
        lines = self.path.read_text().splitlines()
        entries = []
        for i, line in enumerate(lines):
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                if i != len(lines) - 1:
                    raise  # damage in the middle of the file is not a crash artifact
        return entries

    def checkout(self, entry_id: str) -> None:
        """Fork: the next entries continue from `entry_id` instead of the end of the file."""
        if entry_id not in {e["id"] for e in self.load()}:
            raise KeyError(f"no entry {entry_id!r} in {self.path}")
        self.head = entry_id

    def branch(self, leaf_id: str | None = None) -> list[Message]:
        """The messages on the path from the root to `leaf_id` (default: the head), in order.

        How: index the entries by id, walk `parent_id` links back from the leaf to the root,
        then reverse the path. Entries on other branches are never visited, which is what
        makes a fork cheap. Non-message entries on the path (Week 3 adds compaction entries)
        are skipped here.
        """
        leaf_id = leaf_id or self.head
        if leaf_id is None:
            return []
        by_id = {e["id"]: e for e in self.load()}
        path, cur = [], by_id.get(leaf_id)
        while cur:
            path.append(cur)
            cur = by_id.get(cur["parent_id"])
        return [
            MESSAGE.validate_python(e["payload"]) for e in reversed(path) if e["type"] == "message"
        ]
