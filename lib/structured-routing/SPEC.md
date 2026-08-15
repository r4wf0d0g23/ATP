# ATP Structured Routing Contracts

## Contracts

- [`route-decision.schema.json`](../../schema/route-decision.schema.json) describes the result of routing exactly one request.
- [`execution-plan.schema.json`](../../schema/execution-plan.schema.json) describes the single-step or composite DAG produced by an actionable decision.

The contracts deliberately separate outcome from evidence. Semantic retrieval may appear as evidence, but `semantic-support-only` is not sufficient authorization for a state-changing step.

## Dispositions

- `single` / `specific_match`: exactly one non-wildcard protocol was selected.
- `composite` / `composite_match`: two or more protocols were selected and a plan is required.
- `ambiguous` / `ambiguous`: candidates exist but operator resolution is required; execution is not authorized.
- `fallback` / `wildcard_fallback`: one wildcard protocol was selected. It is tracked separately from specific success.
- `none` / `no_route`: no supported route exists.
- `none` / `routing_error`: the router failed to decide; a structured error is required.

Only `single`, `composite`, and `fallback` produce execution plans. Unsupported state-changing requests must remain `ambiguous` or `none`; fallback cannot conceal them.

## Plan invariants

JSON Schema validates shape. Contract tests additionally enforce unique `step_id` and `bundle_id` values, known dependencies, an acyclic graph, and self-dependency rejection. A runtime planner must also serialize steps whose mutation scopes overlap. `serialization_groups` declares that constraint explicitly; absence of an overlap is not evidence that parallel execution is safe unless the conflict engine checked it.

Cross-contract validation is mandatory: every selected protocol must be an authorized candidate with non-semantic authorization evidence; every plan must match its decision and contain only selected protocols; and every pair of overlapping mutation scopes must be ordered by a dependency path or co-listed in a serialization group.

Every step retains its own protocol, vars, tool allowlist, model class, guardrails, checkpoint policy, mutation scope, bundle, and receipt requirement. Composite completion requires every step to reach a terminal state and an aggregate receipt. A plan cannot authorize work outside its corresponding route decision.

## Compatibility and migration

Contracts use semantic versions and reject unknown major versions. Legacy first-match output migrates to `single` only if a specific non-wildcard protocol selection is directly evidenced; wildcard selection migrates to `fallback`. Multiple plausible matches migrate to `ambiguous`, not an arbitrary winner. Legacy routing exceptions migrate to `none` / `routing_error`.

Changing disposition meaning, authorization semantics, or DAG completion rules requires a major version. Adding an optional evidence code or reason code is a minor-compatible vocabulary change only after consumers tolerate it.
