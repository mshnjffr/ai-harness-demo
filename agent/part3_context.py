"""Context / state.

For now this just builds the initial message list for a task. Branch 1 adds
trimming to keep the context from growing without bound (context rot).
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
