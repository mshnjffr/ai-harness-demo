"""The agent loop.

Call model -> if it asked for tools, run them and feed results back -> repeat,
until the model gives a final answer.

This branch has no safety: nothing stops a confused model from looping forever.
That is the point -- the `context-and-guardrails` branch adds them.
"""

import json
import sys
from dataclasses import dataclass, field
from typing import Literal

from .part1_tools import ToolRegistry
from .part2_model import client


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


@dataclass
class LoopResult:
    answer: str
    iterations: int
    trace: list
    stopped_by: Literal["model", "guardrail", "success"]


def run_loop(model: str, messages: list, tools: ToolRegistry) -> LoopResult:
    trace: list = []

    while True:
        iteration_index = len(trace) + 1

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

            trace.append(
                LoopIteration(
                    index=iteration_index,
                    outcome="tool_calls",
                    tool_events=tool_events,
                    context_size=context_size,
                )
            )
