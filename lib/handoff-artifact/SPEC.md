# Handoff Artifact Library

## Purpose

Defines the structured handoff artifact that every sub-agent writes on completion,
partial completion, or timeout. This is the persistence layer that survives orchestrator
compaction — when the Captain's session is compacted, var files and handoff artifacts are
the only recovery paths. Without this layer, partial executions leave infrastructure in
an unknown intermediate state.

> **Canonical schema:** `lib/execution-receipt/schema/handoff-artifact.schema.json`
>
> Execution receipts and handoff artifacts are the same concept — one schema, one location.
> See `lib/execution-receipt/SPEC.md` for the full audit gate spec (T2 scan, violation handling, escalation chain).

---

## Write Rules

- Sub-agent writes artifact **before** returning the result report to the orchestrator
- Artifact is written even on failure — set `result: "failure"` and leave `state_after` reflecting the unchanged state
- `var_updates` is the authoritative list of var IDs for orchestrator write-back — not the prose report
- Orchestrator reads `var_updates`, applies each update to the var files, then archives the artifact

## Artifact Location

```
atp-instance/artifacts/YYYY-MM-DD-<bundle_id>-handoff.json
```

## Artifact Retention

- **Active:** 30 days in `atp-instance/artifacts/`
- **Archive:** After 30 days → `atp-instance/artifacts/archive/`
- **Critical failures** (`result: "failure"`) are retained permanently and never archived

## Schema Reference

See `lib/execution-receipt/schema/handoff-artifact.schema.json` for the full JSON Schema.

Key required fields: `bundle_id`, `protocol_id`, `completed_at`, `execution_phase_reached`,
`result`, `changes`, `var_updates`, `next_action`, `state_after`.
