---
id: bundle-schema
name: Bundle Schema Validator
version: 0.1.0
status: draft
created: 2026-04-08
---

# Bundle Schema Validator

## Purpose

Validates context bundles before they are passed to sub-agents. A bundle that fails validation is rejected before any sub-agent is spawned. This makes multi-protocol contamination a build-time error rather than a runtime risk.

## Validation Rules

### Rule 1: Single Protocol
A bundle MUST declare exactly one `protocol_id`. Bundles with zero or multiple protocol IDs are rejected.

```
FAIL: { protocol_id: ["example-config-protocol", "example-inference-protocol"] }
PASS: { protocol_id: "example-config-protocol" }
```

### Rule 2: Var Scope Containment
Every `var_id` in the bundle MUST be declared in the matched protocol's `requires.vars` list. Vars not declared by the protocol are rejected — even if they exist in the var registry.

```
FAIL: bundle for example-config-protocol includes example-inference-var
PASS: bundle for example-config-protocol includes example-config-state only
```

### Rule 3: Model Class Compliance
The `model_class` assigned to the bundle MUST match or exceed the protocol's minimum model class. Downgrading below protocol minimum is rejected.

```
Protocol minimum: balanced
FAIL: bundle assigns model_class: fast
PASS: bundle assigns model_class: balanced or capable
```

### Rule 4: Guardrail Inheritance
The bundle MUST include all guardrails from the matched protocol. Orchestrator may add guardrails but cannot remove protocol-defined ones.

```
FAIL: bundle omits a guardrail from the protocol definition
PASS: bundle includes all protocol guardrails (may add more)
```

### Rule 5: Task Description Present
The bundle MUST include a non-empty `task_description`. Empty or placeholder task descriptions are rejected.

```
FAIL: { task_description: "" }
FAIL: { task_description: "TODO" }
PASS: { task_description: "Verify current DGX serve params via docker inspect. Restart vllm_nemotron container. Report updated serve params." }
```

### Rule 6: No Credential Fields
The bundle MUST NOT contain any of: API keys, tokens, passwords, private keys, or secret values. Credential-bearing bundles are rejected regardless of other validity.

Detection: scan for keys matching `*_key`, `*_token`, `*_password`, `*_secret`, `*_api*` in bundle content.

## Rejection Behavior

When a bundle fails validation:
1. Log the violation to `atp-instance/reports/bundle-violations-YYYY-MM-DD.json`
2. Do not spawn the sub-agent
3. Pass violation to T3 for root cause analysis
4. T3 determines: orchestrator error (wrong var selection) vs protocol gap (protocol declares wrong vars)
5. T3 corrects the bundle or opens a PR to fix the protocol — does not surface to Raw unless T3 cannot resolve

## Violation Log Format

```json
{
  "violation_ts": "<ISO timestamp>",
  "bundle_id": "<bundle_id>",
  "protocol_id": "<protocol_id>",
  "failed_rules": ["Rule 2: Var Scope Containment"],
  "detail": "var example-inference-var not declared by example-config-protocol",
  "t3_resolution": "removed example-inference-var from bundle, resubmitted",
  "status": "corrected|escalated"
}
```

## Step Duration Metadata

| Step | Expected Duration |
|------|------------------|
| Bundle validation (all rules) | <2s |
| Violation log write | <1s |
| T3 root cause analysis | 30–60s |
| T3 bundle correction + resubmit | 10–20s |
| Total (valid bundle) | <2s |
| Total (invalid bundle, T3 corrects) | 60–90s |
