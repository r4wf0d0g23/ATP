---
id: execution-receipt
name: Execution Receipt Gate
version: 1.0.0
status: draft
created: 2026-04-08
---

# Execution Receipt Gate

## Purpose

No task is considered complete until a handoff artifact (execution receipt) exists in `atp-instance/artifacts/`. The receipt is a required gate, not optional output. T2 scans for tasks that ran without producing a receipt and flags them as protocol violations.

This creates a closed audit loop: every task that enters the system must produce a receipt, and every receipt is verified by T2. Tasks without receipts are not silently accepted as complete — they are flagged, analyzed by T3, and either retroactively documented or marked as violations.

## Receipt Requirements

The receipt schema is defined in `lib/execution-receipt/schema/handoff-artifact.schema.json`. Execution receipts are handoff artifacts — there is one schema, not two.

A valid v1 receipt is a handoff artifact per
`lib/execution-receipt/schema/handoff-artifact.schema.json`. It correlates
`receipt_id`, `run_id`, `plan_id`, `bundle_id`, exact bundle hash, protocol pin,
and variable pins. Ledger validation recomputes canonical hashes and requires
byte-identical pins. Schema validity alone is insufficient.

All required fields must be present. A receipt missing any required field is treated as incomplete and flagged.

## T2 Receipt Scan

T2 runs after each sub-agent completion event and:

1. Checks `atp-instance/artifacts/` for a receipt matching the completed bundle_id
2. If receipt exists and is valid → append `receipt-submitted`; append
   `completed` only after correlation, pin, mutation-evidence, and terminal
   checks pass
3. If receipt missing → flag as violation, pass to T3
4. If receipt incomplete (missing fields) → flag as violation, pass to T3

T3 resolution for missing receipts:
- Preserve logs as evidence, but never reconstruct or fabricate an execution receipt
- Mark the run `violated` if completion evidence is unrecoverable
- Open a PR to the ATP repo documenting the gap if it reveals a protocol deficiency
- Does not surface to Raw unless T3 cannot determine task outcome

## Violation Severity

Severity values use the ATP canonical vocabulary: `info`, `warn`, `critical` (see `lib/escalation/` and `lib/validation/`). `ERROR` is not an ATP severity — recoverable issues are `warn`, halt-level issues are `critical`.

| Scenario | Severity | T3 Action |
|----------|----------|-----------|
| Receipt missing, task outcome recoverable from logs | `warn` | Keep pending; request an attributable receipt |
| Receipt missing, task outcome unrecoverable | `critical` | Mark violated, log gap |
| Receipt present but incomplete fields | `warn` | Reject; request a corrected receipt |
| Receipt forged (bundle_id doesn't match any spawned task) | `critical` | Flag immediately, do not accept |

## Lifecycle ledger and terminal semantics

The ledger is append-only JSONL using
`schema/lifecycle-ledger-event.schema.json`. Each run starts with exactly one
`pending` event at sequence zero. Subsequent events increment sequence by one
and hash-chain to the previous canonical event. Duplicate identical events are
idempotent; the same event ID or sequence with different bytes is tampering.

`completed` is legal only when a valid correlated receipt exists, the receipt
hash is unchanged, all pins match the bundle snapshot, and every observed
mutation is covered by receipt changes/evidence. Crash reconciliation may append
`reconciled`, `failed`, or `violated`; it never appends success by inference.
Emergency bypass requires an operator-hashed identity, reason, and future
expiry and is itself immutable. A bypass does not rewrite history.

Legacy receipts are imported as non-terminal `legacy-observed` evidence in
observe mode (represented privately as a reconciliation reason), never as v1
completion. Warn/enforce require a new attributable v1 receipt.

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
