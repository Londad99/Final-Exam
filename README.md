# Nubara Disruption Companion — Engineering README

**Purpose and scope.** Reduce uncertainty and avoidable contacts through verified disruption explanations and controlled next steps. The backend in [Part - B](Part%20-%20B/RUNBOOK.md) implements the student-approved Google ADK design over airline mocks; no frontend or deployment. The earlier submission supplies reusable contracts and deterministic logic. **Validation: 17 local tests and 4/4 scripted ADK evaluations pass; real Gemini evaluations currently fail with provider HTTP 503. A successful real-model run is still required.**

## 1. Autonomy boundary

| Step | Classification | Reason | Risk | Control / fallback |
|---|---|---|---|---|
| Bind booking | Deterministic | Access control | Cross-booking disclosure | Identity-to-booking check; demo identities only |
| Interpret and select reads | Agentic | Understand passenger intent | Omitted intent or injected instruction | Read-only tools, bounded calls; fail closed |
| Reconcile events | Deterministic | Reproducible trust decisions | Stale/conflicting information | Source priority, freshness, consistency; escalate |
| Estimate connection | Deterministic | Schedule arithmetic | Prediction mistaken for certainty | Report risk; never infer confirmed loss |
| Apply policy/filter options | Deterministic | Eligibility and capacity constraints | Unsupported rights or split party | Versioned rules, unknown-state handling, seats/TTL/fare checks |
| Render and notify | Deterministic | Ground every claim | Unsupported promises | Typed facts, templates, policy validation; queued is not delivered |
| Open case | Deterministic | Enforce policy review | False escalation claim | Durable deduplication; require acknowledgement |
| Decide reserved outcomes | Human | R4/R5 require approval | Unauthorized payment/handling | External operator; workflow stops |
| Confirm option | Human | Passenger consent | Ambiguous authorization | Exact presented option and explicit confirmation |
| Submit change | Deterministic | Protected write | Expiry/duplicates/false success | Revalidate; SQLite claim; unknown outcome escalates |

**Target case.** S1 is delayed 160 minutes. Projecting 17:55 arrival to 20:35 indicates risk for the 19:05 connection, not confirmed loss. R1/R2 thresholds (180/240 minutes) are unmet; R3 stays unknown. R4 compensation and R5 priority handling need human review under `POL-DELAY-2026-03`. O2 has one seat for two passengers; O1 is a next-day candidate, not a free-change guarantee while the penalty is unknown; O3 lacks a validated refund policy. Explain, open a case, and do not rebook or promise payment.

## 2. Agent pattern and architecture

**Workflow Agent in Google ADK**, implemented with `SequentialAgent`: one `LlmAgent` selects reads, then a deterministic `DecisionGate` evaluates and acts. Compared with the earlier fixed pipeline, the LLM interprets natural-language requests and chooses function calls. Multiple reasoning agents and unrestricted action tools were rejected as unnecessary complexity.

```text
API -> authorize/minimize -> SequentialAgent
                              read_agent <-> four read wrappers
                                  -> decision_gate -> validated response/notification
                                                   -> human case -> STOP for operator
                                                   -> offer token -> STOP for passenger
confirmation endpoint -> token/owner/TTL + fresh assessment -> protected rebooking
```

Sequential orchestration connects reader to gate; no model-directed delegation. `read_agent` reaches only trip, events, policy and options wrappers; identifiers remain backend-bound. `decision_gate` alone reaches case/notification writes. The confirmation service alone reaches rebooking. Operator decisions remain outside this slice; no endpoint can impersonate approval.

The target retrieves minimized trip data, then operational/policy/option evidence, then interpreted intent. Typical budget: three model calls, hard cap four, timeout 90 seconds. Gemini is configurable in `.env`; the default is `gemini-3.8-flash`, listed with a [free tier](https://ai.google.dev/gemini-api/docs/pricing). Three calls are demonstrated with the test double, not measured successfully with Gemini. Provider failure returns an explicit unavailable status and referral.

## 3. Context and personal data

Allowlist flight/segment references, airports, dates/times, party size, minor flag, changeable/refundable flags, and completeness metadata. Exclude names, contacts, documents, raw booking/passenger IDs, loyalty tier, exact age, fare family and remarks. Redact known booking identities and identifier patterns from input; typed wrappers exclude raw objects and untrusted remarks. Generic detection of arbitrary personal information is a known limitation.

ADK conversations are ephemeral and deleted after each run. SQLite retains owner-bound confirmation offers and write outcomes, never conversations or contact data. Offer validity is enforced; production retention/deletion remains to be implemented. Traces contain random correlation IDs, tool names and evidence/policy references, not prompts or credentials.

## 4. Tools or RAG; assumptions and validation

Policies use exact versioned tool results and deterministic evaluation; vector similarity cannot establish applicability or completeness. RAG could explain airport facilities from approved guides with document/section/version citations, freshness checks and abstention. It is not implemented and cannot authorize rights.

Approved assumptions: 30-minute relevant delay, 45-minute connection margin, 30-minute event freshness; priority OPS_CORE > AIRPORT_FEED > LEGACY_MIRROR. Degraded/future/unknown sources are excluded; unresolved equal-authority conflicts block affected claims. Unaffected verified facts may still be communicated. The sample clock advances from the exam date; airport-specific timezone/minimum-connection rules need production integration.

Options expire after 120 seconds. A 201 is only PENDING_CONFIRMATION; 409/503 remain indeterminate pending human reconciliation. Durable write claims prevent automatic replay after uncertainty or restart. Tests verify tool trajectories, answers, policy faithfulness and confirmation controls. Evaluation exposed an SQLite connection leak on Windows; explicit connection closing fixed it. See [evidence and limitations](Part%20-%20B/RUNBOOK.md). More referrals trade automation for supported claims. Next: successful real-model evidence, production identity/retention and operator integration. ADK's pinned SequentialAgent API is deprecated but functional; migration is future work.
