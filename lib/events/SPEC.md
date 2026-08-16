# ATP Event Contract

## Status and scope

Version `1.0.0` defines the public, generic envelope used to correlate ATP routing and execution facts. It is an append-only interoperability contract, not a storage or runtime implementation.

Schema: [`schema/atp-event.schema.json`](../../schema/atp-event.schema.json)

## Correlation

Every event has an opaque `event_id` and `request_id`. Producers add `decision_id`, `plan_id`, `run_id`, and `bundle_id` as those objects come into existence. IDs are random or derived from sanitized deterministic test seeds; they must never contain a session key, username, host, filesystem path, or other private identifier. `parent_event_id` expresses causation, while `sequence` provides producer-local ordering. Timestamps are not an ordering guarantee.

Shared canonical correlation IDs use exactly 32 lowercase hexadecimal characters: `dec_<hex32>`, `pln_<hex32>`, `run_<hex32>`, `bnd_<hex32>`, and `rcp_<hex32>`. Producers must not accept shortened, mixed-case, or non-hex variants.

One request must yield exactly one `route.decided` or `routing.failed` terminal routing fact. A routing failure is represented by a route decision whose `disposition` is `none` and whose `match_disposition` is `routing_error`; it is never reported as `no_route`.

## Metric dictionary

Reducers may derive the following metrics without inspecting request or prompt content:

- `requests_total`: distinct `request_id` values with `request.received`.
- `route_decisions_total`: distinct `decision_id` values in `route.decided` or `routing.failed`.
- `routing_exact_total`: decisions with `specific_match`.
- `routing_composite_total`: decisions with `composite_match`.
- `routing_ambiguous_total`: decisions with `ambiguous`.
- `routing_fallback_total`: decisions with `wildcard_fallback`. This must never contribute to exact-match success.
- `routing_none_total`: decisions with `no_route`.
- `routing_errors_total`: decisions with `routing_error`.
- `completion_latency_ms`: `outcome.recorded.occurred_at - request.received.occurred_at`, only for complete correlated pairs.
- `receipt_validity_rate`: valid `receipt.recorded` facts divided by all terminal runs; missing facts stay missing rather than inferred.
- `checkpoint_rate`, `retry_count`, `rollback_count`, `operator_correction_rate`, `token_overhead`, and `estimated_cost`: derived only when an explicit sanitized payload field is present.

Reducers must publish numerator, denominator, malformed-event count, and uncorrelated-event count. They must not silently impute missing events or treat fallback routing as a specific success.

## Privacy and retention

Public contracts and fixtures contain metadata only. Event payloads must not contain prompt or response bodies, secrets, credentials, raw session keys, private variable values, operator identities, or absolute private paths. Protocol IDs and reason codes are permitted only when generic or already public. Producers should hash no sensitive value unless the deployment has a documented keyed-pseudonymization policy; an ordinary hash of a low-entropy secret is not redaction.

The event schema applies these key and value restrictions recursively through nested objects and arrays. Producers must validate the complete payload tree; filtering only top-level fields is non-conforming.

`lib/events/sanitizer.py` is the owning reference sanitizer for payload construction. `reject` mode fails closed on forbidden keys, private paths, and credential-shaped values even when they appear beneath benign keys. `redact` mode returns a deep sanitized copy and never mutates the input. Producers must sanitize first and then validate the result against the event schema; schema validation alone is insufficient for detecting credentials embedded in ordinary string values.

Retention classes are deployment policy labels:

- `ephemeral`: discard after immediate health aggregation.
- `operational`: bounded retention for debugging and deterministic reductions.
- `audit`: retain according to the private deployment's approved audit policy.

The public schema does not prescribe durations. Private deployments must define durations, access control, deletion, and legal requirements outside this repository.

## Compatibility and migration

Schema versions follow semantic versioning. Consumers must reject unknown major versions, may accept a newer minor version only when they ignore unknown event types explicitly, and may accept patch updates without migration. Because schemas set `additionalProperties: false`, producers and consumers should negotiate a minor version before adding fields.

Migration from legacy telemetry is one-way: preserve the original record privately, emit a new v1 event only when its required fields are directly known, attach a new opaque ID, and record `legacy_migrated` in sanitized payload metadata. Never fabricate missing correlations or synthesize a successful route decision. Dual emission is allowed during a bounded rollout; v1 and legacy records must be deduplicated by the v1 `event_id`, not timestamp.
