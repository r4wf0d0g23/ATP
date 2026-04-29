---
id: inter-agent-ops
name: Inter-Agent Operations
version: 0.1.0
status: active
classification: template
# Replace with actual date when instantiating
created: "2000-01-01"
# Replace with actual date when instantiating
last_reviewed: "2000-01-01"
review_authority: deployment-owner
semantic_summary: "Governs communication between agents, secondary agent health checks, and multi-agent task coordination. Triggers when tasks involve sending work to another agent, checking agent status, or routing through inter-agent message paths. Critical guardrail: always use the target agent gateway invoke path, never the calling agent own session endpoint."
preload_size_class: xs
priority: 50

triggers:
  - "secondary agent"
  - "inter-agent"
  - "agent comms"
  - "crew ops"

requires:
  vars:
    - id: example-crew-state
      staleness_policy: session-cache

post_update:
  - example-crew-state

guardrails:
  - "Never route messages through the calling agent's own session endpoint — use the target agent's gateway invoke path"
  - "Set sufficient timeout for secondary agent turns — inference + tool execution may take significantly longer than direct API calls"
  - "Secondary agent config writes must remain disabled unless explicitly authorized"

escalation:
  - "Secondary agent unreachable after 2 invoke attempts — diagnose infrastructure before retrying"
  - "Secondary agent session bloated — reset before next mission-critical task"
  - "Gateway token mismatch — re-authenticate before retrying"
checkpoint_policy:
  on_partial: write-handoff-artifact
  clean_state_definition: "No pending messages awaiting acknowledgment; agent gateway is in a known state"
  rollback: "none — inter-agent messages cannot be unsent; log the partial send state"
tool_allowlist: ["exec", "read"]
---

# Inter-Agent Operations

## Context
Any task involving communication between agents, secondary agent status checks, or multi-agent coordination. This protocol exists because inter-agent comms routing is non-obvious and silent failures are common without explicit health checks and correct routing paths.

## Pre-load Checklist
1. Load `<crew-state-var-id>` — confirm secondary agent gateway URL, token, session key
2. Verify secondary agent is reachable before sending work

## Execution Notes

### Routing rule
Always use the secondary agent's gateway invoke path — never `sessions_send` directly from the primary agent, as it routes to the calling agent's own session.

### Health check before tasking
Verify the secondary agent's gateway health endpoint responds before sending work. A failed invoke against an unreachable agent wastes time and may corrupt session state.

### Timeout budgeting
Secondary agent turns involving tool use and inference can take significantly longer than direct API calls. Set timeouts accordingly — under-budgeting causes false failures.

## Post-execution Checklist
1. If secondary agent status changed (recovered, degraded, reconfigured) → update `<crew-state-var-id>`
2. Log inter-agent comms outcomes in daily memory file
