"""The agent loop.

Call model -> if it asked for tools, run them and feed results back -> repeat,
until the model gives a final answer or a guardrail fires.

Before each model call the loop trims the context (so it cannot grow forever)
and runs the guardrail (so a confused model cannot loop forever).
"""

import json
import sys
from dataclasses import dataclass, field
from typing import Callable, Literal, Optional

from .part1_tools import ToolRegistry
from .part2_model import client
from .part3_context import trim_context
from .part4_guardrails import GuardrailFn, GuardrailInput

MAX_CONTEXT_MESSAGES = 20


@dataclass
class ToolEvent:
    tool: str
    args: dict
    result: str


@dataclass
class LoopIteration:
    index: int
    outcome: Literal["tool_calls", "answer"]
    tool_events: list = field(default_factory=list)
    context_size: int = 0
    context_trimmed: bool = False


@dataclass
class LoopResult:
    answer: str
    iterations: int
    trace: list
    stopped_by: Literal["model", "guardrail", "success"]


# Returns a ToolEvent if the harness handled something (e.g. login), else None.
LoginHandler = Callable[[], Optional[ToolEvent]]


def run_loop(
    model: str,
    messages: list,
    guardrail: GuardrailFn,
    tools: ToolRegistry,
    login_handler: Optional[LoginHandler] = None,
) -> LoopResult:
    trace: list = []

    while True:
        iteration_index = len(trace) + 1

        before_trim = len(messages)
        messages = trim_context(messages, MAX_CONTEXT_MESSAGES)
        context_trimmed = len(messages) < before_trim

        check = guardrail(GuardrailInput(iterations=len(trace), messages=messages))
        if not check.ok:
            stopped_by = "success" if check.reason.startswith("Successfully") else "guardrail"
            return LoopResult(
                answer=check.reason,
                iterations=len(trace),
                trace=trace,
                stopped_by=stopped_by,
            )

        sys.stdout.write(f"[iter {iteration_index}] calling model... ")
        sys.stdout.flush()
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools.definitions,
        )

        choice = response.choices[0]
        context_size = len(messages)
        print(choice.finish_reason)

        messages.append(choice.message.model_dump(exclude_none=True))

        if choice.finish_reason == "stop":
            trace.append(
                LoopIteration(
                    index=iteration_index,
                    outcome="answer",
                    tool_events=[],
                    context_size=context_size,
                    context_trimmed=context_trimmed,
                )
            )
            return LoopResult(
                answer=choice.message.content or "(no response)",
                iterations=len(trace),
                trace=trace,
                stopped_by="model",
            )

        if choice.finish_reason == "tool_calls":
            tool_events: list = []

            for call in choice.message.tool_calls or []:
                name = call.function.name
                args = json.loads(call.function.arguments or "{}")

                tool = tools.by_name.get(name)
                sys.stdout.write(f"           -> {name}({json.dumps(args)}) ... ")
                sys.stdout.flush()
                try:
                    result = tool.execute(args) if tool else f'Unknown tool: "{name}"'
                    print("done")
                except Exception as err:  # noqa: BLE001
                    result = f"Error: {err}"
                    print("error")

                tool_events.append(ToolEvent(tool=name, args=args, result=result))
                messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

            if login_handler is not None:
                login_event = login_handler()
                if login_event is not None:
                    tool_events.append(login_event)
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                "Authentication completed by harness. You are now logged in. "
                                "Navigate back to https://news.ycombinator.com and complete your upvote task."
                            ),
                        }
                    )

            trace.append(
                LoopIteration(
                    index=iteration_index,
                    outcome="tool_calls",
                    tool_events=tool_events,
                    context_size=context_size,
                    context_trimmed=context_trimmed,
                )
            )
