# Architecture

Visual companion to the [README](README.md). These diagrams show what an agent
harness is made of and how the pieces fit together at runtime.

## The branch ladder

Each branch adds exactly one capability. Read a branch, then `git diff` to the
next to see that capability in isolation.

```mermaid
flowchart LR
  main["main: bare loop"] --> cg["context-and-guardrails: trim + guardrails"]
  cg --> hoe["harness-owns-environment: run_harness()"]
  hoe --> vr["verify-and-retry: verify + retry"]
  vr --> lr["login-recovery: auto-login + success guardrail"]
```

## The harness owns the environment

`run_harness()` is the owner: it opens the browser, binds the tools to it,
builds the context, runs the loop, verifies the outcome, and always closes the
browser. Tools never touch the browser lifecycle -- the harness does.

```mermaid
flowchart TB
  TASK["task"] --> HARNESS["run_harness()"]

  subgraph harness [Harness]
    HARNESS --> SESSION["BrowserSession (the environment)"]
    HARNESS --> TOOLS["create_tools(session)"]
    HARNESS --> CTX["create_context(task)"]
    HARNESS --> LOOP["run_loop()"]
    HARNESS --> VERIFY["verify + retry"]
  end

  TOOLS --> SESSION
  LOOP --> MODEL["OpenRouter model"]
  LOOP --> GUARD["guardrails"]
  LOOP --> LOGIN["login_handler"]
  LOGIN --> SESSION
  VERIFY --> RESULT["result + trace"]
```

## One loop iteration

Before every model call the loop trims context and checks the guardrail. The
model either answers (done) or asks for tools; tools run, results are fed back,
and the optional login handler can recover from a redirect before looping again.

```mermaid
flowchart TD
  START["start iteration"] --> TRIM["trim_context()"]
  TRIM --> GCHECK{"guardrail ok?"}
  GCHECK -->|"no"| STOP["return: stopped_by guardrail / success"]
  GCHECK -->|"yes"| CALL["call model with tools"]
  CALL --> FIN{"finish_reason"}
  FIN -->|"stop"| ANSWER["return answer (stopped_by model)"]
  FIN -->|"tool_calls"| RUN["execute tools, append results"]
  RUN --> LOGINH{"login redirect?"}
  LOGINH -->|"yes"| RECOVER["auto-login, inject continue message"]
  LOGINH -->|"no"| NEXT["next iteration"]
  RECOVER --> NEXT
  NEXT --> START
```

## Verify and retry

Guardrails catch *structural* failures (looping, context bloat). Verify catches
*wrong answers* -- a loop can finish "successfully" having done the wrong thing.
A failed verify retries the whole task, unless the failure is fatal.

```mermaid
flowchart TD
  ATTEMPT["run_harness_attempt()"] --> V{"verify result"}
  V -->|"passed"| DONE["return result"]
  V -->|"fatal (e.g. login wall)"| DONE
  V -->|"failed, attempts left"| RETRY["retry"]
  V -->|"failed, no attempts left"| DONE
  RETRY --> ATTEMPT
```
