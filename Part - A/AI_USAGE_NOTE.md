# AI Usage & Decision Note — Part A

## Update process

Maintain this note as work progresses, recording actual AI use, student-approved decisions, revisions and validation evidence. Obtain student acceptance before implementing or documenting important new decisions.

## Tools and purpose

OpenAI Codex was used in this session to read the exam photographs, inspect the previous submission and unfinished autonomy draft, identify discrepancies, and draft Part A in English. The previous submission's note reports Claude Code usage; that historical account has not been independently verified here. No runtime LLM integration or execution occurred in this session.

## Outputs retained, revised and rejected in this draft

- Retained deterministic policy evaluation, source reconciliation, capacity checks, confirmation boundaries and same-action idempotency as design foundations.
- Revised the previous missed-connection assertion: delay propagation produces an estimate, not verified arrival evidence; R3 remains unknown until verified.
- Replaced the optional AI composer in the proposed design with a mandatory tool-calling agent, as the final exam requires.
- Rejected raw booking remarks as model context, automatic compensation, zero fare difference as proof of a free change, and request submission as proof of completed booking.
- Preserved the unfinished autonomy draft's distinction between verified facts, connection risk and preliminary options; translated and consolidated it with items 2–4.

These describe assistant-authored draft changes, not a claim that the student personally accepted every choice.

## Validation and limits

The assistant compared the draft with all three photographs and inspected the prior README, design, privacy utilities, models and connection calculation. This revealed the distinction between projected connection loss and confirmed eligibility, and the missing mandatory agent. Validation was documentary: no new test results, model run, trace, measured latency or verified pagination are claimed. The prior note's reported 29 passing tests belongs to the earlier submission.

## Personal decisions and authorship

The student explicitly requested use of earlier deliverables as the existing baseline and English comments/documentation with Spanish chat. The student rejected the assistant-proposed LangGraph choice and selected Google ADK. The student also required prior acceptance of every important decision before implementation or documentation. Other assistant-authored technical proposals remain pending review. Before submission, the student must add their own account of design choices accepted, changed or rejected and how they validated them. AI-generated text must not stand in for evidence of personal review or work not performed.

## Information excluded from the model

The proposed runtime excludes names, contact details, document numbers, raw booking/passenger identifiers, loyalty information, exact child age, booking remarks, credentials and unrestricted case evidence. Only minimized intent and allowlisted operational facts may reach an approved provider. Models explain facts; code and authorized people control monetary entitlements, policy applicability and authorization.

