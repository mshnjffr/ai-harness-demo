"""Context / state.

Builds the initial message list for a task, and trims old messages so the
context does not grow without bound (context rot). The system prompt and the
original user task are always kept.
"""

SYSTEM_PROMPT = (
    "You are a helpful assistant with access to tools.\n"
    "Use tools whenever they help you give a more accurate answer.\n"
    "When you have enough information, respond directly and concisely."
)


def create_context(task: str) -> list:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]


def trim_context(messages: list, max_messages: int) -> list:
    """Drop the oldest tool/turn messages if context grows too large.
    Always keep the system prompt and the original user task."""
    if len(messages) <= max_messages:
        return messages

    system, user = messages[0], messages[1]
    rest = messages[2:]
    trimmed = rest[len(rest) - (max_messages - 2):]
    return [system, user, *trimmed]
