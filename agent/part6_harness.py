"""The harness.

The harness owns the environment (opens/closes the browser) AND now owns
correctness: after the loop finishes it runs a verify step, and if verification
fails (and the failure is not fatal) it retries the whole task.

Guardrails catch structural failures (looping, context bloat). Verify catches
*wrong answers* -- a loop can finish "successfully" having done the wrong thing.
You need both.
"""

import json
import re
from dataclasses import dataclass
from typing import Callable, Optional

from .browser import BrowserSession
from .part1_tools import create_tools
from .part3_context import create_context
from .part4_guardrails import default_guardrails
from .part5_loop import LoopResult, run_loop


@dataclass
class VerifyResult:
    passed: bool
    reason: str
    fatal: bool = False


@dataclass
class HarnessExecutionResult:
    task: str
    model: str
    result: LoopResult


@dataclass
class HarnessOptions:
    verify: Optional[Callable[[HarnessExecutionResult], VerifyResult]] = None
    max_attempts: int = 1


@dataclass
class HarnessResult:
    task: str
    model: str
    result: LoopResult
    answer: str
    attempts: int
    verification: Optional[VerifyResult]


def run_harness(task: str, model: str, options: Optional[HarnessOptions] = None) -> HarnessResult:
    options = options or HarnessOptions()
    max_attempts = options.max_attempts

    for attempt in range(1, max_attempts + 1):
        execution = run_harness_attempt(task, model)
        verification = options.verify(execution) if options.verify else None
        answer = (
            verification.reason
            if verification is not None and not verification.passed
            else execution.result.answer
        )

        latest = HarnessResult(
            task=execution.task,
            model=execution.model,
            result=execution.result,
            answer=answer,
            attempts=attempt,
            verification=verification,
        )

        if (
            verification is None
            or verification.passed
            or verification.fatal
            or attempt == max_attempts
        ):
            return latest

        print(f"\nAttempt {attempt} failed - retrying ({attempt + 1}/{max_attempts})...\n")

    raise RuntimeError("Harness finished without producing a result")


def run_harness_attempt(task: str, model: str) -> HarnessExecutionResult:
    session = BrowserSession()
    session.open()

    try:
        tools = create_tools(session)
        messages = create_context(task)
        result = run_loop(model, messages, default_guardrails, tools)
        return HarnessExecutionResult(task=task, model=model, result=result)
    finally:
        session.close()


def _url_after_now_at(result: str) -> str:
    parts = result.split("now at ")
    return parts[1].strip() if len(parts) > 1 else ""


def _extract_url(result: str):
    match = re.search(r"https?://\S+", result)
    return match.group(0) if match else None


def _is_login_url(url) -> bool:
    return bool(url) and ("/login" in url or "/vote" in url)


def verify_successful_upvote(execution: HarnessExecutionResult) -> VerifyResult:
    events = [event for it in execution.result.trace for event in it.tool_events]

    for event in events:
        if (
            event.tool == "browser_click"
            and "up_" in json.dumps(event.args)
            and re.search(r"news\.ycombinator\.com/(news)?$", _url_after_now_at(event.result))
        ):
            return VerifyResult(
                passed=True,
                reason=f"Upvote click confirmed - landed on {_url_after_now_at(event.result)}",
            )

    for event in events:
        if event.tool == "harness_auto_login" and event.result.startswith(
            "Harness failed to handle login at "
        ):
            return VerifyResult(passed=False, reason=event.result, fatal=True)

    for event in events:
        if event.tool != "harness_auto_login" and _is_login_url(_extract_url(event.result)):
            return VerifyResult(
                passed=False,
                reason=f"Hit login screen instead of completing the upvote ({_extract_url(event.result)})",
                fatal=True,
            )

    return VerifyResult(passed=False, reason="No successful upvote click found in trace")


def print_harness_result(result: HarnessResult) -> None:
    loop = result.result
    print("\n--- Agent trace ---\n")

    for iteration in loop.trace:
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
    print(f"\nStopped by: {loop.stopped_by} after {loop.iterations} iteration(s)")
    print(f"Attempts:   {result.attempts}")

    if result.verification is not None:
        status = "PASS" if result.verification.passed else "FAIL"
        print(f"Verify:     {status} - {result.verification.reason}")
