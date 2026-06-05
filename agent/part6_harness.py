"""The harness.

This is the architectural decision that makes this a real harness rather than
just a loop with tools: the harness owns the environment. It opens the browser,
binds the tools to it, builds the context, runs the loop, and -- crucially --
always closes the browser in a finally block.

Tools never touch the browser lifecycle. The harness does.
"""

import json
from dataclasses import dataclass

from .browser import BrowserSession
from .part1_tools import create_tools
from .part3_context import create_context
from .part4_guardrails import default_guardrails
from .part5_loop import LoopResult, run_loop


@dataclass
class HarnessExecutionResult:
    task: str
    model: str
    result: LoopResult


def run_harness(task: str, model: str) -> HarnessExecutionResult:
    session = BrowserSession()
    session.open()

    try:
        tools = create_tools(session)
        messages = create_context(task)
        result = run_loop(model, messages, default_guardrails, tools)
        return HarnessExecutionResult(task=task, model=model, result=result)
    finally:
        session.close()


def print_harness_result(execution: HarnessExecutionResult) -> None:
    result = execution.result
    print("\n--- Agent trace ---\n")

    for iteration in result.trace:
        trim_note = " (trimmed)" if iteration.context_trimmed else ""
        ctx = f"[ctx: {iteration.context_size}{trim_note}]"

        if iteration.outcome == "tool_calls":
            print(f"[iter {iteration.index}] {len(iteration.tool_events)} tool call(s) {ctx}")
            for event in iteration.tool_events:
                print(f"  -> {event.tool}({json.dumps(event.args)})")
                snippet = event.result[:120]
                ellipsis = "..." if len(event.result) > 120 else ""
                print(f"     {snippet}{ellipsis}")
        else:
            print(f"[iter {iteration.index}] answered {ctx}")

        print()

    print("--- Result ---\n")
    print(result.answer)
    print(f"\nStopped by: {result.stopped_by} after {result.iterations} iteration(s)")
