# Technical evidence and runbook

## Implemented scope

A local FastAPI backend invokes a Google ADK `SequentialAgent` containing a read-only `LlmAgent` and a deterministic `DecisionGate`. Airline tools are mocks; the real runtime requires Gemini. No frontend, deployment, real booking change, compensation payment or operator interface is included. `Resultado Prueba Anterior` remains the historical baseline; the new package does not import it at runtime.

The model selects four read wrappers and emits three intent flags. A backend lookup before model invocation binds the authorized booking and supports input redaction; the LLM must still request the minimized trip view and remaining reads. The deterministic gate refuses incomplete trajectories. All monetary decisions, source reconciliation, seat checks and writes stay in code. The Spanish passenger reply is a deterministic template, not unchecked model prose.

## Install and run (PowerShell)

Run from `Part - B` with Python 3.11 or newer (validated here with Python 3.14.7):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[test]'
# Only if .env does not already exist:
Copy-Item .env.example .env
# Edit .env locally and set GOOGLE_API_KEY. Never paste keys into commands or logs.
.\.venv\Scripts\python.exe scripts/demo.py
.\.venv\Scripts\python.exe -m uvicorn nubara_agent.api:app --host 127.0.0.1 --port 8000
```

The requested `.env` already exists locally and is ignored by Git. `.env.example` contains no credential. `GEMINI_MODEL` defaults to `gemini-3.8-flash`. No paid fallback is configured. The provider publishes a free tier, but project eligibility/quota depends on the account. Do not enable billing to run this exam.

`requirements-lock.txt` records this environment; `pyproject.toml` pins direct dependencies. The script exits unsuccessfully when the real model does not complete; a safe fallback is not marked as a successful agent run.

## API examples

The API uses explicit **mock identity headers**, not production authentication. Keep it bound to localhost. `demo-maria` may access only `ABC123`; `demo-adults` only `ABC456`. The latter is an additional adults-only, 200-minute-delay fixture that exercises an eligible rebooking path; it does not change the exam target.

```powershell
$headers = @{ 'X-Demo-User' = 'demo-maria' }
$body = @{ message = 'Mi vuelo a Lima está retrasado. Viajo con un menor. ¿Alcanzamos México? Si no, quiero cambiar al vuelo de esta noche. ¿Cuánto me pagan de compensación?' } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/v1/disruptions/ABC123/assess -Headers $headers -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($body))
```

For the control fixture, assess `ABC456` with `X-Demo-User: demo-adults` and a rebooking question without requesting compensation. If the response is `CONFIRM_OPTION`, inspect the itinerary, then submit its token and option:

```json
POST /v1/disruptions/confirm
X-Demo-User: demo-adults
{"confirmation_token":"TOKEN_FROM_RESPONSE","option_id":"O1","confirmed":true}
```

Do not interpret `PENDING_CONFIRMATION` as a completed booking. The target case has no confirmation token because human review is required. Tokens are owner-bound and expire with the offer. No endpoint accepts a client-provided human-approval flag.

## Architecture and least privilege

| Component | Responsibility | Access | Connection |
|---|---|---|---|
| API / authorization / sanitizer | Bind mock identity and minimize passenger input | Private booking lookup, no writes | Calls ADK runner with sanitized input |
| `disruption_workflow` | Fixed orchestration | No business tools | `SequentialAgent` invokes reader then gate |
| `read_agent` | Interpret intent and select read functions | Trip/events/policy/options wrappers only | ADK function calling; no sub-agent delegation |
| `decision_gate` | Reconcile, apply rules, validate response | Deterministic engine; guarded cases and notifications | Fixed next stage; no LLM approval |
| Confirmation service | Resume an explicitly selected offer | Fresh deterministic reads, protected rebooking, escalation | Separate API request and owner-bound SQLite token |
| Human operations | Resolve reserved or unknown outcomes | Outside this demo | Workflow stops after case creation |

An option requires fresh availability, matching route, sufficient seats, zero fare difference and a valid no-fee entitlement before becoming confirmable. Candidate options are never executable. Unknown material rules fail closed; unknown R3 does not negate an independently valid R1 entitlement. R4/R5 always stop automatic rebooking. Unknown 503 results are not retried automatically; the same persisted write claim returns the uncertainty and opens a case. A 409 is also escalated because the sample has no request-status lookup contract.

SQLite claims are committed before external writes. A crash can therefore leave an indeterminate result, but cannot justify sending a fresh duplicate. Confirmation state survives process restart. The replay clock starts at the exam timestamp and advances; its epoch persists so a restart cannot revive an expired offer.

## Validation commands and evidence

```powershell
.\.venv\Scripts\python.exe -m pytest -q --disable-warnings
.\.venv\Scripts\python.exe scripts/evaluate.py
.\.venv\Scripts\python.exe scripts/evaluate.py --live
```

- `tests/test_workflow.py`: 17 passing tests through ADK dispatch and deterministic controls, including API behavior, authorization, source precedence, unknown rules, expiry and write deduplication across restart/new offers.
- `evidence/offline-evaluation.json`: 4/4 required scenarios passing, explicitly labeled `scripted_adk_test_double`. Checks both tool trajectories and answers; failed writes include the full confirmation/revalidation trajectory.
- `evidence/live-evaluation.json`: 0/4 passing because Gemini returned HTTP 503. These are failed real attempts, not substitutes for a successful model-driven trace.
- `evidence/latest-real-trace.json` and `latest-real-response.json`: latest single target attempt and its safe fallback; individual trace files retain earlier attempts.
- `evidence/pytest-results.txt`: latest local test summary.

Every entitlement must match the exact evaluated rule, policy version and approval status. Schema checks alone are not treated as proof of faithfulness. Model requests are tested for fixture PII absence; committed traces exclude request text, raw tool payloads, keys and confirmation tokens.

**Failure found and fixed:** the first offline evaluator failed on Windows because SQLite connection context managers commit/rollback but do not close connections. Explicit `closing()` now releases handles; the four-case evaluator completes. A review also caught lower-priority delay values being aggregated instead of using the reconciled source; a regression test covers it.

## Current limits and next steps

1. A successful real-model run is outstanding. Gemini 2.5 Flash returned 404 (unavailable for new users); Gemini 3.8 Flash and a diagnostic 3.1 Flash-Lite request returned 503/high demand. Retry the live commands once service recovers; do not claim completed Part B(b) evidence until a real trajectory passes.
2. Scripted models prove orchestration and controls, not Gemini's intent recognition, stability or prompt-injection resistance. The injection test proves remarks do not enter model context and writes cannot bypass guards.
3. Mock identity headers are not authentication. Mock writes are in-memory upstream; local deduplication is persistent, but real operators and a durable airline backend are not integrated.
4. The itinerary sample supports conservative estimates, not authoritative arrival/MCT data. The 30/45/30-minute design thresholds need operations validation. Live cancellation, multi-airport and timezone-complete handling remain outside scope.
5. Known booking names and identifier patterns are redacted; arbitrary PII inside free text is not guaranteed to be detected. SQLite access relies on local OS permissions; retention cleanup, encryption and production identity must be added before real passengers.
6. ADK 2.14.0 still supports `SequentialAgent` but marks it deprecated in favor of its newer Workflow API. The pinned version preserves this implementation; migration needs a separate reviewed change. TestClient also emits a dependency deprecation warning. Neither warning is suppressed as a claimed fix.
7. The model is limited to four calls and 90 seconds; a valid but longer trajectory fails safely. Real latency/token measurements are unavailable while the provider fails. No RAG, frontend, deployment or production retry queue was added.

## References

- [Google ADK workflow orchestration](https://codelabs.developers.google.com/devsite/codelabs/build-agents-with-adk-orchestrating-agent-workflows)
- [Google ADK Python source](https://github.com/google/adk-python)
- [Gemini API pricing and free tier](https://ai.google.dev/gemini-api/docs/pricing)
