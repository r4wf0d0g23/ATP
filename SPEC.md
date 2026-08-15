# Agent Task Protocol (ATP) Specification

**Version:** 0.2.0  
**Status:** Active  
**Maintainer:** Primary Agent  
**Review Authority:** Deployment Owner  

---

## Purpose

ATP is a structural protocol layer that governs how agents handle context-required interactions. It eliminates drift, loss, and inaccuracy by enforcing a deterministic context lifecycle for every interaction that requires external knowledge, state, or infrastructure awareness.

ATP is not a task runner. It is the **interaction scaffold** that every task runs inside.

---

## Execution Tiers

ATP defines two execution tiers. Every agent run is classified as one or the other before the execution loop begins.

### Orchestration Tier

The orchestrator holds **operational context only**: topology, crew state, deployment architecture, dispatch tables. It never holds task-specific execution vars. When a task arrives:

1. Match task to an orchestration protocol
2. Determine which execution protocol handles it
3. Assemble a **context bundle** — the exact vars and guardrails the sub-agent needs
4. Spawn a sub-agent with the bundle (isolated session)
5. Receive outcome report
6. Write any state changes back to var files
7. Never execute the task directly

This tier eliminates context collision: the orchestrator never holds execution state, so there is nothing to collide.

### Execution Tier

The executor receives a context bundle from the orchestrator and runs exactly one protocol in an isolated session. It:

1. Loads only the vars in its context bundle
2. Runs the ATP execution loop for its assigned protocol
3. Returns a structured outcome report
4. Terminates — no persistent state survives the session

Sub-agents never write to var files. They report facts; the orchestrator writes them.

### Tier Detection

An agent determines its tier at session start:
- If spawned with a `context_bundle` payload → **execution tier**
- If running in a persistent named session or responding to a user → **orchestration tier**
- If running a cron job → **orchestration tier** (cron runner is an orchestrator)

See `lib/orchestration/SPEC.md` for the full two-tier model and context bundle spec.

---

## Core Execution Loop

Every context-required interaction follows this exact sequence. No exceptions.

```
INPUT
  ↓
CONTEXT DETERMINATION
  Classify the task. Identify which protocol applies.
  If no protocol matches → proceed without ATP pre-load (log as protocol needed).
  ↓
CONTEXT VARIABLE VALIDATION
  For each required variable in the matched protocol:
    - Check staleness policy
    - If stale or never-verified → run verify_cmd before proceeding
    - If verification fails → halt and surface error before execution
  ↓
CONTEXT PRE-LOAD
  Load all required vars and docs declared by the protocol.
  Inject into agent context before execution begins.
  ↓
INTERACTION EXECUTION
  Execute the task with pre-loaded context.
  Never assume variable values not explicitly validated this session.
  ↓
POST-EXECUTION CONTEXT REVIEW
  Compare pre-load state against any state changes made during execution.
  For each variable that may have changed → flag for update.
  Write updates or new protocol to var files immediately. Do not defer.
  ↓
OUTPUT
  Deliver result. Include post-execution var update confirmation if applicable.
```

---

## Canonical Execution Phases

The ATP execution loop consists of exactly 6 phases. These phase names are the authoritative values used in `execution_phase` and `execution_phase_reached` fields across all library schemas (`lib/outcome/`, `lib/escalation/`, `lib/execution-receipt/`).

| Phase | Description |
|---|---|
| `context-determination` | Classify the task. Identify which protocol applies. |
| `variable-validation` | Check staleness policy for each required var. Run verify_cmd if stale. |
| `context-preload` | Load all required vars and docs into agent context. |
| `interaction-execution` | Execute the task with pre-loaded context. |
| `post-execution-review` | Compare pre-load state against state changes. Flag vars for update. |
| `output` | Deliver result. Confirm post-execution var updates if applicable. |

Any schema that enumerates execution phases must include all 6 values above.

---

## Protocol Definition

A protocol is warranted when a task meets **one or more** of the following threshold criteria:

1. Requires ≥2 external context sources (docs, vars, live state)
2. Has post-execution state that must be persisted back to variables
3. Involves infrastructure that can change between sessions (containers, endpoints, deployments)
4. Failure to pre-load context has historically caused incorrect outputs
5. The task recurs across sessions with consistent context requirements

A protocol is **not** warranted for:
- Single-context, stateless tasks (simple lookups, one-shot calculations)
- Tasks where all required context is fully contained in the current conversation

### Protocol File Format

```yaml
---
id: protocol-id                    # kebab-case, unique
name: Human Readable Name
version: 0.1.0
status: active                     # active | draft | deprecated
created: YYYY-MM-DD
last_reviewed: YYYY-MM-DD
review_authority: owner            # role identifier: who approves PRs for this protocol

triggers:                          # keywords/patterns that activate this protocol
  - "config change"
  - "openclaw config"

requires:
  vars:                            # variables that must be loaded before execution
    - id: var-id
      staleness_policy: always-verify | session-cache | ttl:Nd | on-change-only
  docs:                            # external docs to fetch before execution
    - url: https://...
      section: optional-section-anchor

post_update:                       # variables to review/update after execution
  - var-id

guardrails:                        # hard rules enforced during execution
  - "Rule text"

escalation:                        # when to stop and surface to the review authority
  - "Condition text"
---

# Protocol Name

## Context
Brief description of what this protocol covers and why it exists.

## Pre-load Checklist
Explicit list of what must be loaded/verified before execution begins.

## Execution Notes
Protocol-specific guidance for the execution phase.

## Post-execution Checklist
What must be reviewed and potentially updated after execution completes.
```

---

## Variable Definition

Variables are named caches for infrastructure state, configuration values, and other context that changes over time and must be verified rather than assumed.

### Variable File Format

```yaml
---
id: var-id                         # kebab-case, unique
name: Human Readable Name
version: 0.1.0
status: active                     # active | deprecated
created: YYYY-MM-DD
last_verified: YYYY-MM-DD
verified_by: agent-id              # which agent last verified
staleness_policy: always-verify    # default policy when protocol doesn't override

verify_cmd: |                      # command to run to verify current value
  ssh host 'command'

source: live | config | derived    # where the value comes from
---

# Variable Name

## Current Value
<!-- Updated by agent after each verification -->

## Change History
| Date | Value | Changed By | Notes |
|------|-------|------------|-------|

## Notes
Protocol-specific usage notes, gotchas, dependencies.
```

---

## Staleness Policies

| Policy | Behavior |
|---|---|
| `always-verify` | Run `verify_cmd` every time before using. No exceptions. Use for live infrastructure state (container params, running services). |
| `session-cache` | Verify once per session. Reuse within the same session without re-verifying. Use for config state that doesn't change mid-session. Optional `:Nm` suffix (e.g. `session-cache:30m`) sets a within-session TTL of N minutes. Equivalent to `session_ttl_minutes: N`. If both are set, the smaller value wins. |
| `ttl:Nd` | Trust for N days. Re-verify if `last_verified` is older than N days. Use for slow-changing state (model registry, package IDs). |
| `on-change-only` | Trust until an explicit change event is logged. Use for human-managed state (review authorities, escalation contacts). |

---

## Review Chain

| Action | Reviewer | Turnaround |
|---|---|---|
| Staleness review PR (agent-generated) | Primary Agent | Next session |
| New protocol PR | Deployment Owner | Async, no SLA |
| Emergency variable update (live infra change) | Primary Agent immediate-write | Same session |
| Deployment Owner ratification of emergency updates | Deployment Owner | Within 24h |

### Staleness Review Loop

The `atp-protocol-review` protocol governs continuous staleness maintenance:
- A sub-agent periodically scrubs all protocols and vars for drift
- If drift detected → opens a PR against ATP repo with proposed updates
- PR reviewed by Primary Agent before merge
- Merged changes propagate to all agents at next bootstrap

---

## Library Reference

Each library in `lib/` addresses a specific gap in the ATP execution loop. Read the library's `SPEC.md` before implementing that layer. Libraries are grouped by purpose.

### Orchestration & intake

| Library | Gap Addressed | Key Schema | Status |
|---|---|---|---|
| `lib/orchestration/` | Single-agent model has no role separation; orchestrator and executor share context, causing collision | _n/a (architectural spec)_ | active |
| `lib/task-intake/` | Tasks reach Captain without protocol routing; no pre-Captain intake gate | _n/a_ | draft |
| `lib/conflict/` | Multiple protocol matches have no precedence rule | `conflict-rule.schema.json` | active |
| `lib/protocol-index/` | String-match trigger classification doesn't scale; no RAG layer | `index-entry.schema.json` | active |
| `lib/structured-routing/` | First-match routing cannot represent composition, ambiguity, fallback, or an execution DAG | `route-decision.schema.json`, `execution-plan.schema.json` | contract |

### Context bundles & sub-agent dispatch

| Library | Gap Addressed | Key Schema | Status |
|---|---|---|---|
| `lib/bundle-schema/` | Context bundles built ad-hoc; no build-time validation that protocol/var ids exist | _n/a (cross-registry validation contract)_ | draft |
| `lib/bundle-prompt/` | Sub-agent prompts assembled inconsistently; quality regressions from prompt-order drift | _n/a (canonical XML structure)_ | active |
| `lib/jit-context/` | Bundles eagerly load var content, accumulating staleness; sub-agent may never need the loaded content | _n/a (resolution contract)_ | active |
| `lib/tool-scope/` | Sub-agents inherit full orchestrator tool set; bloated tools degrade execution quality | _n/a (allowlist contract)_ | active |

### Variables & validation

| Library | Gap Addressed | Key Schema | Status |
|---|---|---|---|
| `lib/frontmatter/` | YAML frontmatter extraction algorithm undefined; bridge between Markdown files and JSON Schema layer | `frontmatter.schema.json` | active |
| `lib/validation/` | Variables trusted without integrity checks; no poisoning detection | `validation-result.schema.json` | active |
| `lib/auto-correct/` | Drift corrections applied silently; no boundary on what may be auto-fixed without human review | _n/a (correction policy)_ | draft |
| `lib/dependency/` | No var-to-var dependency graph; load order undefined | `dependency-graph.schema.json` | active |
| `lib/session-freshness/` | Session-cache vars drift stale mid-session without detection | `freshness-state.schema.json` | active |

### Budgets & resource control

| Library | Gap Addressed | Key Schema | Status |
|---|---|---|---|
| `lib/context-budget/` | Pre-load exceeds model context limits silently | `budget-check.schema.json` | active |
| `lib/window-budget/` | Session-window budget tracking absent; long sessions silently exhaust available tokens | _n/a_ | active |

### Execution lifecycle

| Library | Gap Addressed | Key Schema | Status |
|---|---|---|---|
| `lib/checkpoint/` | Timed-out sub-agents leave infrastructure in unknown intermediate states with no recovery path | _n/a (checkpoint policy)_ | active |
| `lib/handoff-artifact/` | Sub-agent partial executions leave no recovery breadcrumb after orchestrator compaction | `handoff-artifact.schema.json` | active |
| `lib/execution-receipt/` | No closed audit loop; tasks can complete without producing a verifiable handoff artifact | `lib/execution-receipt/schema/handoff-artifact.schema.json` (canonical) | draft |
| `lib/outcome/` | No feedback loop; staleness review has no quality signal | `outcome.schema.json` | active |
| `lib/escalation/` | Escalation rules exist but have no routing or ack structure | `escalation-event.schema.json` | active |
| `lib/events/` | Routing and execution facts lack a versioned, privacy-safe correlation contract and metric vocabulary | `atp-event.schema.json` | contract |

### Autonomous QA & enforcement

| Library | Gap Addressed | Key Schema | Status |
|---|---|---|---|
| `lib/workers/` | No autonomous QA/validation layer; no cost-scaled progression model | `worker-job.schema.json`, `worker-report.schema.json` | active |
| `lib/enforcement-plugin/` | ATP routing is advisory; no transport-layer enforcement that every task is matched to a protocol before dispatch | _n/a (OpenClaw plugin, no schema)_ | draft |

---

## Agent Bootstrap Requirement

Every agent workspace must include `ATP_AGENT.md` at the workspace root. This file is auto-injected by OpenClaw's bootstrap system and ensures ATP is active from the first turn of every session.

The ATP hook (`workspace/hooks/atp/`) implements the execution loop at the OpenClaw hook layer:
- `agent:bootstrap` — injects `ATP_AGENT.md`, loads protocol dispatch table
- `message:preprocessed` — classifies task, validates vars, enriches context
- `message:sent` — triggers post-execution var review

---

## Classification Model

Every protocol and variable must declare a `classification` in its frontmatter.

| Classification | Scope | Where it lives |
|---|---|---|
| `public` | Generic pattern, no deployment-specific data | ATP repo (`protocols/` or `vars/`) |
| `template` | Public pattern with placeholder values, illustrates structure | ATP repo (`templates/`) |
| `private` | Deployment-specific values, live infrastructure state, credentials refs | Instance deployment only — never in public repo |

### Classification rules

- A protocol is `public` if its triggers, guardrails, and escalation rules apply generically across any deployment of that pattern.
- A protocol is `private` if it contains hostnames, credentials paths, infrastructure-specific commands, or organization-specific logic.
- A protocol that has both a generic pattern AND deployment-specific execution details must be **split**: a `template` version in the ATP repo and a `private` instance file in the deployment that extends it.
- All variable files with real values are `private` by definition — they contain live state. Only structural template examples may be `public`.

### Handling in creation and review

| Step | Public/Template | Private |
|---|---|---|
| **Creation** | PR to ATP repo, reviewed by deployment owner before merge | Written directly to instance deployment; no PR to ATP repo |
| **Review (staleness)** | PR to ATP repo with proposed changes | Updated directly in instance deployment by primary agent |
| **Emergency update** | Not applicable (public content doesn't hold live state) | Primary agent immediate-write; deployment owner ratification within 24h |
| **Repo exposure** | Safe to publish, fork, share publicly | Must never appear in public repo; treat as operational secrets |

---

## Protocol Index

The ATP repo maintains an index of **public and template protocols only**. Instance deployments maintain their own private protocol index separately.

| ID | Name | Classification | Status |
|---|---|---|---|
| `atp-protocol-review` | ATP Protocol Review (Meta) | `template` | active |
| `agent-config-change` | Agent Config Change | `template` | active |
| `infra-ops` | Infrastructure Operations | `template` | active |
| `memory-maintenance` | Memory Maintenance | `public` | active |
| `inter-agent-ops` | Inter-Agent Operations | `template` | active |

*Instance-specific protocols (deployment tooling, project-specific workflows) belong in the instance deployment and are not listed here.*

---

## Variable Index

The ATP repo contains **no real variable values**. Only structural examples live here.

| ID | Name | Classification | Notes |
|---|---|---|---|
| `example-your-var-id` | Example variable template | `template` | Shared placeholder id used by `templates/vars/live-state.md` and `templates/vars/config-state.md`; replace when instantiating |

*All variables with real values are `private` and live in the instance deployment only.*

---

## Schema Versioning

### Current Version
ATP schemas are at version **0.1.0**.

### Backwards-Compatibility Policy
When a new **required** field is added to a schema:
1. It enters a **30-day grace period** during which its absence is treated as `warn` (not `fail`) by T1 and T3 validators
2. After the grace period, absence becomes `critical`
3. T1 automatically opens migration PRs for non-conformant files during the grace period

When a field is **removed or renamed**, that is a breaking change and requires a **major version bump**.

### Version Bump Criteria
| Change type | Version bump |
|-------------|-------------|
| New optional field | patch (0.1.0 → 0.1.1) |
| New required field | minor (0.1.0 → 0.2.0) |
| Removed/renamed field | major (0.1.0 → 1.0.0) |
| Enum value added | patch |
| Enum value removed | major |

### Migration Responsibility
T1 detects non-conformant files and opens PRs. The deployment owner reviews and merges.
Protocol/variable files do not carry a schema_version field — they are validated against the current schema at scan time.
