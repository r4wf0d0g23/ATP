# ATP Orchestration Library

## Purpose

Defines the two-tier agent execution model. ATP v0.1.0 assumed a single agent running
protocols sequentially. This extension introduces **orchestration tier** and **execution
tier** as distinct roles with separate context scopes, eliminating context collision by
architectural design rather than runtime conflict detection.

---

## The Problem This Solves

When a single agent holds multiple active protocols simultaneously (e.g. DGX container
restart + crew comms to Nav in the same session), vars from different protocols can
contradict each other mid-session. A state change in one protocol silently invalidates
a var loaded by another. There is no deterministic resolution — outcomes depend on
load order and session history.

**Root cause:** ATP v0.1.0 has no concept of *who* is loading a protocol. It assumes one
agent runs everything sequentially in one context window.

**Solution:** Split execution into two tiers with hard context scope boundaries. The
orchestrator never holds execution state. Sub-agents never hold cross-task state.
Collision is impossible by construction.

---

## Two-Tier Model

### Tier: Orchestration (Captain)

**Role:** Decision-maker, task router, state aggregator.

**Context scope:**
- Deployment topology (what agents exist, what they can do)
- Crew state (agent health, endpoints, current assignments)
- Architecture references (what protocols exist, what context bundles they require)
- Outcome reports from completed sub-agent tasks

**Does NOT hold:**
- Task-specific execution vars (`example-inference-var`, `example-deploy-var`, etc.)
- Live infrastructure state (container args, on-chain state, config file contents)
- Tool outputs from execution tasks

**Execution behavior:**
- Receives a task
- Matches it to an orchestration protocol
- Determines which sub-agent type handles it and what context bundle they need
- Spawns the sub-agent with the context bundle
- Receives the outcome report
- Updates vars from the report (Captain owns the write path, not the sub-agent)
- Never executes the task directly

### Tier: Execution (Sub-agent)

**Role:** Single-task executor with bounded context.

**Context scope:**
- Exactly one protocol
- Vars declared by that protocol only
- No session history from the orchestrator
- No awareness of other concurrent sub-agents

**Execution behavior:**
- Receives a context bundle from the orchestrator
- Runs the ATP execution loop for its assigned protocol
- Returns a structured outcome report
- Session terminates — no persistent state

---

## Context Bundle

The unit of handoff from orchestrator to sub-agent. Contains everything the sub-agent
needs and nothing it doesn't.

```yaml
context_bundle:
  protocol_id: <id>           # Which execution protocol to run
  var_ids: [<id>, ...]        # Vars to load (subset of protocol's declared requires)
  task_description: <string>  # Human-readable task for the sub-agent
  guardrails: [<string>, ...] # Merged from matched protocol (orchestrator may add more)
  reporting_schema: <id>      # Which outcome schema to use for the response
  session_type: isolated      # Always isolated for execution tier
  model_class: fast|balanced|capable  # Orchestrator assigns model class
```

Schema: `schema/context-bundle.schema.json`

---

## Orchestration Protocols

Orchestration protocols are a new protocol subtype. They differ from execution protocols:

| Field | Execution Protocol | Orchestration Protocol |
|---|---|---|
| `protocol.tier` | `execution` (default) | `orchestration` |
| `requires.vars` | execution vars (example-inference-var, etc.) | topology vars only (crew-state, model-registry) |
| `requires.docs` | SoPs, deployment guides | architecture refs, dispatch tables |
| `guardrails` | execution safety rules | routing and delegation rules |
| `escalation` | execution failure paths | sub-agent failure handling |
| `post_update` | execution state vars | outcome-derived var updates |

Orchestration protocols do not run `verify_cmd` on infrastructure vars. They read
topology and architecture context, make routing decisions, and delegate.

---

## Dispatch Table Structure (Two-Layer)

ATP dispatch now has two layers:

### Layer 1 — Orchestration Dispatch (Captain reads this)

Maps task patterns to: sub-agent type + context bundle recipe.

```
task pattern → {
  sub_agent_type: fast|balanced|capable,
  execution_protocol_id: <id>,
  var_ids: [<id>, ...],
  model_class: fast|balanced|capable
}
```

### Layer 2 — Execution Dispatch (Sub-agent reads this)

Maps protocol ID to: vars + guardrails + reporting schema.
This is the existing ATP dispatch table — unchanged.

---

## Orchestrator State Ownership

All persistent state flows through the orchestrator:

```
Sub-agent executes task
  ↓ returns outcome report
Orchestrator reads report
  ↓ extracts state changes
Orchestrator updates var files
  ↓ commits to disk
Next sub-agent spawned with fresh, accurate vars
```

Sub-agents never write to var files directly. They report facts; the orchestrator
writes them. This ensures var state is always consistent with orchestrator knowledge.

---

## Failure Handling

When a sub-agent fails or is blocked:

1. Orchestrator receives failure outcome report
2. Checks orchestration protocol escalation rules
3. May retry with different model class, different context bundle, or surface to operator
4. Never attempts to execute the task itself — escalate or reassign only

---

## Relationship to Other Libraries

- `lib/dependency/` — still applies to execution-tier var load order within a context bundle
- `lib/conflict/` — collision detection is now a build-time check on the orchestration
  dispatch table, not a runtime check (no two execution protocols in the same bundle)
- `lib/workers/` — T1/T2/T3 workers are execution-tier agents; the cron runner is
  effectively an orchestrator that spawns them
- `lib/context-budget/` — context budget applies per tier: orchestrator budget excludes
  execution vars; sub-agent budget is bounded by the context bundle

---

## Window Budget
See `lib/window-budget/SPEC.md`.

## JIT Context
See `lib/jit-context/SPEC.md`.

## Handoff Artifact
See `lib/handoff-artifact/SPEC.md`.

## Tool Scope
See `lib/tool-scope/SPEC.md`.

## Checkpoint Policy
See `lib/checkpoint/SPEC.md`.

## Bundle Prompt
See `lib/bundle-prompt/SPEC.md`.

## Schema

See `schema/context-bundle.schema.json` and `lib/execution-receipt/schema/handoff-artifact.schema.json`.
