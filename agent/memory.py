"""Short-term session memory: a FIFO buffer of the conversation's text turns.

Just enough context for follow-ups like "...and at Chong Hua?" or "...how about an MRI
instead?". We store only the user/assistant *text* turns (not the intermediate tool
calls), capped so the buffer stays small. Nothing is persisted to disk -- health-related
questions must not survive the session (privacy).
"""

from dataclasses import dataclass, field


@dataclass
class SessionMemory:
    max_turns: int = 20  # keep the last N text turns
    turns: list[dict] = field(default_factory=list)

    def add(self, role: str, content: str) -> None:
        if not content:
            return
        self.turns.append({"role": role, "content": content})
        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.max_turns :]  # FIFO eviction

    def add_user(self, text: str) -> None:
        self.add("user", text)

    def add_assistant(self, text: str) -> None:
        self.add("assistant", text)

    def history(self) -> list[dict]:
        """Prior turns to prepend as LLM context (excludes the current question)."""
        return list(self.turns)

    def clear(self) -> None:
        self.turns.clear()
