# Execution contracts v1 migration

This migration covers variable freshness (D04), lifecycle receipts (D05),
immutable pins (D06), and context plans (D08). It changes public contracts only;
it does not enable runtime enforcement.

## Compatibility profiles

- `legacy-read`: parse existing date-only variables, ID-only bundles, and v0.1
  receipts for inventory. Never interpret them as fresh, reproducible, or
  terminally complete.
- `observe`: construct v1 objects alongside legacy behavior and report
  mismatches without blocking.
- `warn`: require v1 for new runs and warn on legacy inputs. Read-only legacy
  work may use the protocol's explicit degradation policy.
- `enforce`: reject unpinned bundles, stale/unattested required variables, and
  terminal completion without a correlated v1 receipt and ledger chain.

Roll back enforcement by moving from `enforce` to `warn` or `observe`. Do not
delete attestations, snapshots, ledger events, receipts, violations, or pins.

## Field migration

- Variable `last_verified` (date) → `last_verified_at` (RFC 3339 instant).
  Existing dates remain readable but are unknown-time/stale until a validator
  produces an attestation. Never synthesize a time from a date.
- Bundle `protocol_id`/`var_ids` → content-addressed `protocol_pin` and
  `variable_pins`, plus `run_id`, `plan_id`, `context_plan_id`, plugin version,
  and canonical bundle hash. `var_ids` is a deprecated display/scope hint.
- Receipt v0.1 → receipt v1 with exact correlation IDs, bundle hash, and pins.
  A legacy receipt may be inventoried but cannot close a v1 ledger run.
- Whole-document injection → content-free context plan. Legacy protocols use
  deterministic `full` fallback until stable section IDs are authored.

## Cross-contract checks outside JSON Schema

Draft-07 cannot enforce ordering, hash recomputation, time comparisons, or
cross-document equality. Implementations must enforce the checks specified in
the bundle, freshness, receipt, ledger, and context-plan specs. In particular,
schema-valid does not mean correlated, fresh, untampered, or complete.

The dependency-free reference implementation is
`lib/contracts/validator.py`. Its stable error codes are exercised by
adversarial tests and are the minimum owning-layer behavior for runtime work.

## Privacy boundary

Public fixtures use generic IDs and placeholder hashes. Runtime snapshots,
variable values, prompt bodies, session identifiers, operator identifiers, and
raw evidence remain in the private instance. Public objects carry hashes and
redacted summaries only.
