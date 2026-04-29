# ATP Outcome Library

## Purpose
Closes the feedback loop. Records structured outcomes for every protocol execution so the staleness review loop has a quality signal, failure patterns are discoverable, and protocol effectiveness can be measured over time.

## Result Classification

| Result | Criteria |
|---|---|
| `success` | All ATP phases completed. Pre-load validated. Execution completed. Post-execution var updates written. |
| `partial` | Execution completed but post-execution review was incomplete — vars that should have been updated were not, or update was deferred. |
| `failure` | Execution halted at or before the interaction-execution phase. Pre-load failed, validation failed, or budget check failed. |

## Recording Trigger

An outcome record is written at the end of every protocol execution (whether success, partial, or failure). Never deferred.

**Who writes it:** The agent, in the post-execution review phase.

**Where it goes:** `atp-instance/outcomes/YYYY-MM.jsonl` — one JSON object per line, one file per month.

## Quality Signals for Staleness Review

The staleness review (`atp-protocol-review` protocol) uses outcome history to assess protocol health:

| Signal | Threshold | Action |
|---|---|---|
| Failure rate > 20% in last 30 days | Any protocol | Flag for review — guardrails or vars may be wrong |
| `vars_missed_update` appears in > 10% of outcomes | Any protocol | Post-execution checklist may be incomplete |
| Same escalation fires in > 3 consecutive executions | Any escalation rule | Rule may be too sensitive or underlying issue unresolved |
| `partial` rate > 30% | Any protocol | Post-execution phase needs reinforcement |
| Zero outcomes in > 14 days for active protocol | Any protocol | Protocol may be miscategorized (triggers not matching) |

## Protocol Improvement Loop

```
Outcome records accumulate
  ↓
Staleness review reads outcomes/YYYY-MM.jsonl
  ↓
Computes quality signals per protocol
  ↓
If threshold breached → opens PR with proposed protocol update
  ↓
Deployment owner reviews PR
  ↓
Merged update improves protocol accuracy
```

This loop runs automatically via the `atp-protocol-review` protocol.

## Canonical Execution Phases

The `execution_phase_reached` field uses the canonical phase list defined in the root `SPEC.md`. Any update to that list must be reflected here and in `schema/outcome.schema.json`.

## Schema

See `schema/outcome.schema.json`.
