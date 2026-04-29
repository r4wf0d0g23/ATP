---
id: infra-ops
name: Infrastructure Operations
version: 0.1.0
status: active
classification: template
# Replace with actual date when instantiating
created: "2000-01-01"
# Replace with actual date when instantiating
last_reviewed: "2000-01-01"
review_authority: deployment-owner
semantic_summary: "Governs tasks involving live infrastructure state: service management, container configuration, parameter verification, and runtime state updates. Triggers when tasks reference running services, containers, endpoints, serve parameters, or require live state verification before acting. Distinguishes from agent-config-change by operating on running systems rather than configuration files."
preload_size_class: md
priority: 50

triggers:
  - "<infra-system-name>"
  - "container restart"
  - "serve parameters"
  - "infrastructure config"

requires:
  vars:
    - id: example-infra-state
      staleness_policy: always-verify
    - id: example-model-registry
      staleness_policy: ttl:7d
  docs:
    - url: https://<your-infra-docs-url>

post_update:
  - example-infra-state

guardrails:
  - "Always run verify_cmd before assuming any infrastructure state value — never use memory alone"
  - "After any infrastructure change, update the corresponding var file in the same session immediately"
  - "Do not restart services casually — confirm downtime impact before acting"
  - "State changes must be persisted to var files before the session ends"

escalation:
  - "Service fails to start after restart attempt — surface to deployment owner, do not retry blindly"
  - "Verify_cmd returns unexpected output — halt, investigate before proceeding"
  - "Resource constraints detected during operations — halt, verify budget before continuing"
checkpoint_policy:
  on_partial: write-handoff-artifact
  clean_state_definition: "No running services are in a transitional state; all started services are healthy"
  rollback: "<restore previous container/service state — specify per instantiation>"
tool_allowlist: ["exec", "read"]
---

# Infrastructure Operations

## Context
Any task involving live infrastructure: service management, configuration changes, parameter verification, or state updates. This protocol ensures infrastructure state is always verified from the live source before acting, and that changes are immediately recorded.

## Pre-load Checklist
1. Run `verify_cmd` for all `always-verify` vars — never skip this step
2. Check service health before making changes
3. Load any relevant documentation declared in `requires.docs`

## Execution Notes

### Verify without disrupting running services
Use inspection commands that read state without modifying it (e.g., `docker inspect`, config reads, status checks) before any modification.

### After any state change
Immediately update the relevant var file. Do not defer to end of session — if the session ends unexpectedly, the update is lost.

## Post-execution Checklist
1. All changed infrastructure state recorded in var files
2. If service was restarted — confirm it came back healthy before closing
3. Log all changes and observations in the daily memory file
