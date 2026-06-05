# ai-harness-demo

A minimal **Python** implementation of an **agent harness**, built to teach the
team what a harness actually is and how one is put together, running on
**OpenRouter**.

You learn it **branch by branch**: each branch adds exactly one harness
capability. Read the code on a branch, then `git diff` to the next branch to see
what that capability looks like in isolation. The progression is:

```
main  ->  1-context-and-guardrails  ->  2-harness-owns-environment  ->  3-verify-and-retry  ->  4-login-recovery
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for mermaid diagrams of the harness, the
loop, and the verify/retry flow.

---

## What is an AI harness?

An AI harness is the infrastructure that gives a model tools and manages
input/output behind the scenes, so the model has the tools, context, and
environment to do what's asked. It's the scaffolding around an LLM that turns
"answer one prompt" into "do real work in a loop."

The one-liner: **an AI harness is everything except the model weights.**

In practice that means tool interfaces, context/memory handling, guardrails,
verification steps, recovery loops, and logging. Anthropic calls their Claude
Agent SDK a "general-purpose agent harness"; OpenAI calls the same idea
orchestration; the context layer is what Anthropic calls context engineering.

## What is harness engineering?

The discipline crystallized when Mitchell Hashimoto named it:

> Whenever an agent makes a mistake, you engineer the environment so it won't
> make that mistake again.

The job shifts from writing code to **designing environments, specifying intent,
and providing structured feedback**. A harness has three core components:

1. **Context engineering** -- decide what to include/exclude at each model call:
   isolation, reduction (drop stale data to avoid context rot), retrieval.
2. **Architectural constraints** -- guardrails enforced deterministically, not
   just "asked for" in the prompt.
3. **Verification & feedback loops** -- check outputs; if something is wrong,
   surface it so the agent (or engineer) can fix it.

This repo makes all three visible in working code.

---

## The two meanings of "harness"

The word has two distinct usages, and conflating them causes real confusion.
**This repo implements the agent harness** (right column). The eval harness is
described here for contrast only -- there is no `eval/` folder.

| | Eval harness | Agent harness (this repo) |
|---|---|---|
| **Origin** | ML research, ~2021 | Agentic engineering, ~2026 |
| **Example** | EleutherAI's LM Evaluation Harness | Claude Agent SDK, this repo |
| **Purpose** | Measure model quality vs known answers | Enable a model to act in the real world |
| **Input** | Fixed dataset | Open-ended task |
| **Output** | Scores, pass/fail | Answer + tool-call log |
| **Loop** | One call per test case | Iterates until done or a guardrail fires |
| **Tools** | None | Yes -- the whole point |
| **Guardrails** | Not needed | Essential |
| **State** | Stateless | Conversation history across turns |

---

## What's in the `agent/` folder

```
task -> [tools + context + guardrails + loop + verify + recovery] -> result
```

| File | Part | What it does |
|---|---|---|
| `part1_tools.py` | Tool registry | `create_tools(session)` -- tools are bound to the environment the harness provides, not a global they reach into. |
| `part2_model.py` | Model client | OpenRouter via the OpenAI SDK. Swap models by changing one string. |
| `part3_context.py` | Context / state | Builds initial context; trims old messages to prevent context rot. |
| `part4_guardrails.py` | Guardrails | Composable checks (max iterations, max messages, stop-after-success) run before every iteration. |
| `part5_loop.py` | Agent loop | Call model -> run tools -> feed results back -> repeat. Stops on answer, guardrail, or success. |
| `part6_harness.py` | The harness | Owns the lifecycle: opens the environment, runs the loop, verifies the result, retries, closes the environment. |
| `part7_index.py` | Entry point | Wires a task + model into the harness. |
| `browser.py` | Environment | A `BrowserSession` (Playwright) -- one isolated page per run, owned by the harness. |
| `login_handler.py` | Recovery | Detects a login redirect and handles auth itself (`4-login-recovery` branch). |

### The task

> Upvote the highest-ranked not-yet-voted story on Hacker News.

It's a good teaching task because it needs live tools (no hallucinating an
answer), it has a verifiable outcome (did the upvote land?), and it hits a real
obstacle (HN redirects you to a login wall), which motivates verification and
harness-managed recovery.

---

## Learn it branch by branch

Each branch builds on the previous one. Check one out, read it, then diff forward.

| Branch | Adds | Key idea |
|---|---|---|
| **`main`** | Bare loop: tools, model, context, loop, browser. Guardrails and harness are empty placeholders; `part7_index.py` wires things by hand. | A loop with tools is *not yet* a harness. With no guardrails it can spin forever. |
| **`1-context-and-guardrails`** | Context trimming + composable guardrails (`max_iterations`, `max_messages`), checked before every iteration. | Context engineering + architectural constraints. |
| **`2-harness-owns-environment`** | `run_harness()` / `print_harness_result()`. The harness opens and (always) closes the browser; `part7_index.py` collapses to one call. | **The harness owns the environment.** |
| **`3-verify-and-retry`** | `verify_successful_upvote` + a retry loop (`max_attempts`). | Guardrails catch *structural* failures; verify catches *wrong answers*. You need both. |
| **`4-login-recovery`** | `login_handler.py` auto-handles the login redirect; `stop_after_upvote` success guardrail; loop gains a login hook. | Harness engineering: move the missing capability out of the model and into the environment. |

```sh
git checkout main
git diff main 1-context-and-guardrails                       # context-trimming + guardrails
git diff 1-context-and-guardrails 2-harness-owns-environment  # the harness owns the environment
git diff 2-harness-owns-environment 3-verify-and-retry        # verify + retry
git diff 3-verify-and-retry 4-login-recovery                  # harness-managed recovery
```

### The harness owns the environment (`2-harness-owns-environment` onward)

```
run_harness()
  |- session  = BrowserSession()     <- harness opens the environment
  |- tools    = create_tools(session)  <- tools bound to this session
  |- messages = create_context(task)   <- fresh context for this task
  |- result   = run_loop(...)          <- loop runs inside the environment
  |- verify + retry                    <- harness owns correctness
  \- session.close()                   <- always, even on error
```

Tools don't manage the browser. The harness opens it, the harness closes it.
That is what "managing input/output behind the scenes" means in practice.

---

## Setup

```sh
cp .env.example .env
# add your OPENROUTER_API_KEY (get one at https://openrouter.ai)

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

python -m agent.part7_index
```

The model is set in `agent/part2_model.py`:

```python
MODEL = "openai/gpt-oss-120b:free"
```

Swapping in a weaker model is a one-line change -- a good way to watch the
guardrails, verify step, and retry loop actually do their job.

The `4-login-recovery` branch needs a **throwaway** Hacker News account in `.env`
(`HN_USERNAME` / `HN_PASSWORD`). Every earlier branch runs fully without it.

---

## Sources

- Mitchell Hashimoto, *My AI Adoption Journey* (2026) -- coined "harness engineering"
- Anthropic, *Effective context engineering for AI agents*
- EleutherAI, *lm-evaluation-harness* -- the older eval-harness meaning (2021)
