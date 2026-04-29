---
id: task-intake
name: Task Intake Gate
version: 0.1.0
status: draft
created: 2026-04-08
---

# Task Intake Gate

## Purpose

Every task that enters the system passes through the intake gate before reaching the Captain session. The gate determines whether a task maps to a known protocol. If it does, a context bundle is assembled and routed. If it does not, the task is held in `protocol-needed` state and analyzed before proceeding.

The gate is what makes ATP structural rather than advisory. Without it, the Captain session receives raw tasks and decides ad-hoc whether to route them through a protocol — which means protocol compliance is optional. With the gate, there is no path from task arrival to execution that bypasses a protocol.

## Gate Logic

```
task arrives
  ↓
pattern match against orchestration dispatch table
  ↓
match found?
  ├── YES → assemble context bundle → route to sub-agent
  └── NO  → hold as protocol-needed
              ↓
              T3 analyzes: does this task fit an existing protocol with different phrasing?
              ├── YES → reframe task, route through matched protocol
              └── NO  → log as genuine protocol gap
                          ↓
                          T3 proposes new protocol draft
                          ↓
                          PR opened to ATP repo
                          ↓
                          task held until protocol is merged and active
```

## Protocol-Needed State

A task in `protocol-needed` state is not dropped and not executed. It is held in `atp-instance/intake/held-YYYY-MM-DD-HHMMSS.json`:

```json
{
  "held_at": "<ISO timestamp>",
  "task_description": "<original task text>",
  "match_attempt": "no protocol matched",
  "t3_analysis": "<T3 reasoning about what protocol this needs>",
  "proposed_protocol_id": "<id if T3 can propose one>",
  "pr_url": "<PR URL if T3 opened a draft protocol PR>",
  "status": "held|resolved|abandoned"
}
```

## Pattern Matching Algorithm

1. Normalize task text (lowercase, strip punctuation)
2. Test against each protocol's `triggers` list (substring match)
3. If multiple protocols match, select highest `priority` value
4. If no match, pass to T3 for semantic analysis

T3 semantic analysis uses the full orchestration dispatch table as context and determines whether the task is a novel phrasing of an existing protocol or a genuinely new task class.

## Guardrails

- No task executes without a matched protocol — no exceptions
- T3 analysis is mandatory for unmatched tasks — skip is not allowed
- Held tasks are never silently dropped — status must be updated to `resolved` or `abandoned` with rationale
- Protocol-needed PRs are opened within one T3 analysis cycle
- The gate does not modify task content — it routes as-is or holds as-is

## Integration with OpenClaw

The gate runs as a pre-processing step before the Captain session receives a task. Implementation path:

1. OpenClaw `hooks.onMessage` (if available) — intercepts before session routing
2. Fallback: Captain session BOOT.md injection — Captain reads dispatch table first, matches before acting
3. Long-term: native OpenClaw ATP plugin that enforces gate at the transport layer

Current implementation (fallback): ATP_HOOK.md + BOOT.md injection ensures the Captain's first action on any task is pattern matching. The hook enforces this by making it the first instruction in the bootstrap context.

## Step Duration Metadata

| Step | Expected Duration |
|------|------------------|
| Pattern match (dispatch table scan) | <1s |
| T3 semantic analysis (unmatched task) | 30–60s |
| Protocol-needed file write | <2s |
| PR open for draft protocol | 15–20s |
| Total (matched path) | <3s |
| Total (unmatched path) | 60–90s |

Orchestrator timeout for intake: 120s covers both paths with 1.5× buffer.
