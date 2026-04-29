# ATP Escalation Library

## Purpose
Provides structured routing, context packaging, and acknowledgment tracking for escalation events. Transforms escalation rules from strings into actionable, routable, auditable events.

## Severity Levels

| Severity | Behavior | Execution |
|---|---|---|
| `info` | Awareness only. No action required from authority. | Continue execution |
| `warn` | Action recommended. Non-blocking. | Continue execution, flag in output |
| `critical` | Action required. Execution halts until acknowledged. | HALT |

## Escalation Lifecycle

```
Escalation rule triggers during execution
  ↓
1. PACKAGE CONTEXT
   Collect: protocol_id, trigger_text, execution_phase,
   current var states, validation results, last action taken

2. CLASSIFY SEVERITY
   From protocol frontmatter: escalation_severity per rule
   Default: warn

3. ROUTE
   From instance routing table: who receives this escalation?
   Delivery method: channel message, session event, or log-only

4. HALT (if critical)
   Suspend execution. Record escalation-event with requires_ack: true.

5. AWAIT ACKNOWLEDGMENT (if critical)
   Do not proceed until ack_received = true.
   On ack: resume execution from the phase where escalation triggered.

6. RECORD
   Write escalation-event to atp-instance/escalations/YYYY-MM.jsonl
```

## Routing Table

Instance deployments define `atp-instance/escalation-routing.json`:

```json
{
  "routes": [
    {
      "severity": "critical",
      "delivery": "channel",
      "target": "<channel-id-or-session-key>",
      "routed_to": "deployment-owner"
    },
    {
      "severity": "warn",
      "delivery": "log",
      "routed_to": "primary-agent"
    },
    {
      "severity": "info",
      "delivery": "log",
      "routed_to": "primary-agent"
    }
  ]
}
```

## Required Protocol Field

Each escalation entry can optionally declare severity:

```yaml
escalation:
  - text: "Service fails to start after restart"
    severity: critical    # optional, default: warn
  - text: "Unexpected output from verify_cmd"
    severity: warn
```

When `severity` is absent, default is `warn`.

## Unresolved Escalation Detection

A `critical` escalation with `requires_ack: true` and `ack_received: false` after 24 hours is an unresolved escalation. The staleness review flags these as stale and re-routes to the deployment owner.

## Canonical Execution Phases

The `execution_phase` field uses the canonical phase list defined in the root `SPEC.md`. Any update to that list must be reflected here and in `schema/escalation-event.schema.json`.

## Schema

See `schema/escalation-event.schema.json`.
