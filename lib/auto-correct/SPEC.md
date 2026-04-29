---
id: auto-correct
name: Auto-Correct Library
version: 0.1.0
status: draft
created: 2026-04-08
---

# Auto-Correct Library

## Purpose

T1 detects drift between live system state and var-file-defined expected state. T2 applies corrections within pre-approved boundary parameters. Human is only in the loop when a correction falls outside those boundaries.

This eliminates the pattern where drift is detected, reported to a human, human reads report, human approves, human is the bottleneck. Instead: boundary parameters ARE the approval. If a value is within the pre-approved range, T2 applies it automatically.

## Boundary Policy Block

Each var file gains an optional `boundary_policy` block in its YAML frontmatter:

```yaml
boundary_policy:
  auto_correct: true
  allowed_values:
    - "1d"
    - "2d"
    - "7d"
    - "14d"
    - "30d"
  escalate_on_outside: true
```

Or for numeric/duration ranges:

```yaml
boundary_policy:
  auto_correct: true
  allowed_range:
    min: "1d"
    max: "30d"
  escalate_on_outside: true
```

Fields:
- `auto_correct` — whether T2 can apply corrections without human approval
- `allowed_values` — discrete allowed values (use OR with allowed_range, not both)
- `allowed_range` — min/max duration or numeric range
- `escalate_on_outside` — if true, surface to Raw via ops-console when value is outside bounds; if false, skip silently

## T1 Scanner Output Format

T1 writes a structured drift report to `atp-instance/reports/drift-YYYY-MM-DD-HHMMSS.json`:

```json
{
  "scan_ts": "2026-04-08T16:00:00Z",
  "drifts": [
    {
      "var_id": "openclaw-config-state",
      "field": "session.maintenance.pruneAfter",
      "expected": "2d",
      "actual": "absent",
      "within_boundary": true,
      "correction": "2d",
      "execution_protocol": "example-config-protocol"
    }
  ],
  "unverifiable": [],
  "clean": []
}
```

## T2 Decision Logic

```
for each drift in report:
  if verify_cmd failed:
    mark var as unverifiable
    escalate to Raw — do not assume current value is correct
    continue

  if drift.within_boundary == true and auto_correct == true:
    spawn execution sub-agent with correction bundle
    log correction to daily memory
    update var file last_verified
  else:
    surface to Raw via ops-console with drift details
    do not apply
```

## Guardrails

- T2 NEVER applies corrections outside `allowed_values` or `allowed_range`
- T2 NEVER modifies auth tokens, model API keys, or credential fields regardless of boundary policy
- Any correction to a `classification: private` var requires a log entry in daily memory
- If T1 verify_cmd returns non-zero exit, mark as `unverifiable` — escalate, do not correct
- Corrections are applied via the appropriate execution protocol (not inline) — T2 spawns a sub-agent

## Integration Points

- **T1 scanner cron:** runs `verify_cmd` for all vars, writes drift report
- **T2 watcher:** triggered by new drift report file, processes each drift entry
- **Execution sub-agent:** spawned by T2 for each in-boundary correction, uses the correct execution protocol per var
- **Handoff artifact:** written after each correction batch to `atp-instance/artifacts/`

## Example: Session Retention Drift

Scenario: `session.maintenance.pruneAfter` is found absent in live config.
- T1 runs verify_cmd → detects missing field → `within_boundary: true` (absent→"2d" is within 1d–30d range)
- T2 spawns `example-config-protocol` sub-agent with correction bundle
- Sub-agent applies `pruneAfter: "2d"`, restarts gateway, updates var file
- T2 logs: "Auto-corrected openclaw-config-state: session.maintenance.pruneAfter absent→2d"
- No human involvement required
