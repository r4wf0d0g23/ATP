# ATP Validation Library

## Purpose
Ensures variable values are structurally valid and free from poisoning before being injected into agent context. Validation runs after `verify_cmd` returns output but before the value is used.

## Validator Types

| Type | Use for |
|---|---|
| `ssh-command` | Output of SSH-executed inspect/status commands |
| `json-config` | Config file reads, JSON API responses |
| `package-id` | On-chain package IDs, deployment identifiers |
| `endpoint` | URL reachability and response shape checks |
| `regex` | Custom pattern matching for structured strings |
| `custom` | Deployment-specific validators defined in instance |

Each validator type has a spec file in `validators/`.

## Validation Pipeline

```
verify_cmd output
  ↓
1. FORMAT CHECK
   Does the output match the expected structure for this validator type?
   If not → status: fail

2. VALUE CHECK
   Does the value fall within expected ranges/patterns?
   If not → status: fail

3. ANOMALY DETECTION
   Does the value differ unexpectedly from previous_value_hash?
   Is the value suspiciously identical to stale session state?
   Are there injection-like patterns in string values?
   If anomalies found → status: warn (or poison-suspected if critical patterns match)

4. HASH RECORD
   Compute SHA-256 of validated value.
   Compare against previous_value_hash (if available).
   Record current hash for next comparison.
```

## Poisoning Patterns

Values are flagged as `poison-suspected` when any of the following match:

| Pattern | Signal |
|---|---|
| Value contains `<!--`, `<script>`, `\n\n#`, `\n\nSystem:` | Prompt injection attempt |
| Value is identical to a value from a prior session but verify_cmd is `always-verify` | Stale cache injection |
| Numeric value is outside 3σ of historical range | Statistical anomaly |
| String value contains path traversal sequences (`../`, `..\\`) | Path injection |
| JSON value contains unexpected top-level keys not in the expected schema | Schema poisoning |
| Value length is zero or exceeds 10x the expected maximum | Truncation or overflow attack |

Full catalogue: `validators/poisoning-patterns.md`

## Semantic Summary Quality (T3)

NOTE: minLength: 50 is a floor, not a quality gate. T3 deep validation additionally checks
that the summary contains at least 2 distinct semantic concepts not present in the protocol
name alone. Summaries that merely restate the name at length will fail T3 quality review.

## Required Variable Field

```yaml
validator: ssh-command | json-config | package-id | endpoint | regex | custom
```

## Schema

See `schema/validation-result.schema.json`.
