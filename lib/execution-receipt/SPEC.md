---
id: execution-receipt
name: Execution Receipt Gate
version: 0.1.0
status: draft
created: 2026-04-08
---

# Execution Receipt Gate

## Purpose

No task is considered complete until a handoff artifact (execution receipt) exists in `atp-instance/artifacts/`. The receipt is a required gate, not optional output. T2 scans for tasks that ran without producing a receipt and flags them as protocol violations.

This creates a closed audit loop: every task that enters the system must produce a receipt, and every receipt is verified by T2. Tasks without receipts are not silently accepted as complete — they are flagged, analyzed by T3, and either retroactively documented or marked as violations.

## Receipt Requirements

The receipt schema is defined in `lib/execution-receipt/schema/handoff-artifact.schema.json`. Execution receipts are handoff artifacts — there is one schema, not two.

A valid receipt is a handoff artifact per `lib/execution-receipt/schema/handoff-artifact.schema.json` with the following required fields: `bundle_id`, `protocol_id`, `completed_at`, `execution_phase_reached`, `result`, `changes`, `var_updates`, `next_action`, `state_after`.

All required fields must be present. A receipt missing any required field is treated as incomplete and flagged.

## T2 Receipt Scan

T2 runs after each sub-agent completion event and:

1. Checks `atp-instance/artifacts/` for a receipt matching the completed bundle_id
2. If receipt exists and is valid → mark task complete, update var `last_verified`
3. If receipt missing → flag as violation, pass to T3
4. If receipt incomplete (missing fields) → flag as violation, pass to T3

T3 resolution for missing receipts:
- Reconstruct receipt from sub-agent session logs if recoverable
- If unrecoverable: mark task as `completed-without-receipt` and log the protocol violation
- Open a PR to the ATP repo documenting the gap if it reveals a protocol deficiency
- Does not surface to Raw unless T3 cannot determine task outcome

## Violation Severity

Severity values use the ATP canonical vocabulary: `info`, `warn`, `critical` (see `lib/escalation/` and `lib/validation/`). `ERROR` is not an ATP severity — recoverable issues are `warn`, halt-level issues are `critical`.

| Scenario | Severity | T3 Action |
|----------|----------|-----------|
| Receipt missing, task outcome recoverable from logs | `warn` | Reconstruct and log |
| Receipt missing, task outcome unrecoverable | `critical` | Mark violated, log gap |
| Receipt present but incomplete fields | `warn` | Reconstruct missing fields if possible |
| Receipt forged (bundle_id doesn't match any spawned task) | `critical` | Flag immediately, do not accept |

## Audit Trail

All receipt violations logged to `atp-instance/reports/receipt-violations-YYYY-MM-DD.json`:

```json
{
  "scan_ts": "<ISO timestamp>",
  "violations": [
    {
      "bundle_id": "<id>",
      "protocol_id": "<id>",
      "severity": "info|warn|critical",
      "detail": "<what was missing or wrong>",
      "t3_resolution": "<what T3 did>",
      "status": "resolved|violated"
    }
  ]
}
```

## Escalation Chain

```
Task completes
  ↓
T2 scans for receipt
  ↓
Receipt valid? → YES → task complete
             → NO  → T3 analyzes
                       ↓
                       T3 recoverable? → YES → reconstruct receipt, log `warn`
                                       → NO  → mark `critical`, open ATP PR for gap
                                                 ↓
                                                 T3 cannot resolve? → `critical` escalation to Raw
```

Raw only receives `critical` escalations — forged receipts or systemic receipt failures indicating a protocol is broken.

## Step Duration Metadata

| Step | Expected Duration |
|------|------------------|
| T2 receipt scan | <5s |
| Receipt validation (field check) | <1s |
| T3 log reconstruction attempt | 30–60s |
| Receipt write (sub-agent side) | <2s |
| Violation log write | <2s |
| Total (valid receipt) | <6s |
| Total (missing receipt, T3 recovers) | 60–90s |
