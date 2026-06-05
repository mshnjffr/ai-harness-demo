"""Guardrails: composable safety checks that run before every loop iteration.

A guardrail takes the current loop state and returns GuardrailResult.ok() to
continue or GuardrailResult.stop(reason) to halt. They catch *structural*
failures (looping forever, context blowing up) -- not wrong answers. (Catching
wrong answers is the verify step, added in the `verify-and-retry` branch.)
"""

from dataclasses import dataclass
from typing import Callable


@dataclass
class GuardrailResult:
    ok: bool
    reason: str = ""

    @staticmethod
    def proceed() -> "GuardrailResult":
        return GuardrailResult(ok=True)

    @staticmethod
    def stop(reason: str) -> "GuardrailResult":
        return GuardrailResult(ok=False, reason=reason)


@dataclass
class GuardrailInput:
    iterations: int
    messages: list


GuardrailFn = Callable[[GuardrailInput], GuardrailResult]


def max_iterations(limit: int) -> GuardrailFn:
    def check(state: GuardrailInput) -> GuardrailResult:
        if state.iterations >= limit:
            return GuardrailResult.stop(f"Guardrail: reached iteration limit ({limit})")
        return GuardrailResult.proceed()

    return check


def max_messages(limit: int) -> GuardrailFn:
    def check(state: GuardrailInput) -> GuardrailResult:
        if len(state.messages) > limit:
            return GuardrailResult.stop(
                f"Guardrail: context too large ({len(state.messages)} messages)"
            )
        return GuardrailResult.proceed()

    return check


def combine_guardrails(*fns: GuardrailFn) -> GuardrailFn:
    def check(state: GuardrailInput) -> GuardrailResult:
        for fn in fns:
            result = fn(state)
            if not result.ok:
                return result
        return GuardrailResult.proceed()

    return check


default_guardrails = combine_guardrails(
    max_iterations(15),
    max_messages(50),
)
