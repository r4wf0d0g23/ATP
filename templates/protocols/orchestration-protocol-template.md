---
id: example-protocol-id
name: <Human Readable Name>
version: 0.1.0
status: active
tier: orchestration
classification: template
created: "2000-01-01"
last_reviewed: "2000-01-01"
review_authority: deployment-owner
semantic_summary: "<min 50 chars. What orchestration decisions does this protocol govern? What task patterns does it match? What sub-agents does it spawn?>"
preload_size_class: sm

triggers:
  - "<task pattern keyword>"
  - "<task pattern keyword>"

requires:
  vars:
    - id: crew-state
      staleness_policy: session-cache
    - id: model-registry
      staleness_policy: ttl:7d
  # NOTE: orchestration protocols load topology vars only.
  # Never declare execution vars (<your-inference-var-id>, <your-deploy-var-id>, etc.) here.

routing:
  # Maps task sub-types to execution protocols + context bundle recipes.
  # Each entry becomes a context bundle when the orchestrator spawns a sub-agent.
  # Replace example values with your real protocol/var ids (kebab-case).
  - task_pattern: "deploy a service"
    execution_protocol: example-deploy-protocol
    var_ids: [example-deploy-state]
    model_class: balanced

guardrails:
  - "Never execute tasks directly — always delegate to a sub-agent via context bundle"
  - "Never load execution vars (<your-inference-var-id>, <your-deploy-var-id>, etc.) in the orchestrator session"
  - "If no routing entry matches, surface to operator — do not attempt execution"

escalation:
  - "Sub-agent returns failure outcome → retry with higher model_class before surfacing to operator"
  - "Sub-agent times out → surface bundle_id and task_description to operator"

post_update:
  # Orchestrator updates these vars from sub-agent outcome reports.
  # Replace with kebab-case var ids you actually maintain.
  - example-state-var
---

# <Human Readable Name>

## Context
What orchestration decisions does this protocol govern? Why does it exist as a separate
orchestration protocol rather than being handled inline?

## Routing Logic

### <Sub-task type 1>
- **Execution protocol:** `<id>`
- **Vars in bundle:** `<var-id>`, `<var-id>`
- **Model class:** `fast|balanced|capable`
- **Task description template:** "<what to pass as task_description to sub-agent>"

## Outcome Report Handling

For each routing entry, describe what state changes to expect in the outcome report
and which vars to update from those changes.

## Post-execution Checklist
1. Read outcome report from sub-agent
2. Extract state changes → update relevant var files
3. Log to daily memory file
