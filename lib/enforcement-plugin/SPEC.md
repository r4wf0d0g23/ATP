# lib/enforcement-plugin

**Status:** planned

## Purpose

The enforcement-plugin library provides transport-layer enforcement ensuring every
dispatched task is matched to an ATP protocol before execution begins. Without it,
ATP routing is advisory only — a sub-agent can be spawned without a matched protocol
and there is no gate preventing unprotocol-ed work from reaching execution.

## Planned Responsibilities

- **Pre-dispatch gate:** Intercept sub-agent spawn calls and verify a protocol
  match exists before allowing dispatch. Reject (or surface to operator) any task
  that has no matching protocol.
- **Protocol-match attestation:** Attach a `matched_protocol_id` annotation to the
  context bundle so execution-tier protocols can verify they were dispatched correctly.
- **Audit trail:** Emit an enforcement event (accepted / rejected / bypassed) for
  each dispatch attempt, consumable by `lib/execution-receipt/`.
- **Bypass policy:** Define when and how operator-approved bypasses are recorded,
  so the audit log remains complete even for exception cases.

## Integration Points

- `lib/protocol-index/` — queried to resolve the matched protocol for a given task.
- `lib/execution-receipt/` — receives enforcement events as part of the handoff artifact.
- `lib/task-intake/` — enforcement gate sits between intake classification and dispatch.

## Schema

No JSON schema is defined for this library (OpenClaw plugin, no data schema).
Configuration is managed via the OpenClaw plugin manifest.

## Open Questions

1. Should the gate be synchronous (block dispatch) or asynchronous (flag post-hoc)?
2. What is the operator UX for approving a bypass?
3. How are enforcement events surfaced in the `lib/execution-receipt/` handoff artifact?
