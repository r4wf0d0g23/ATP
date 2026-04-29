# Tool Scope Library

## Purpose

Defines the tool allowlist contract for execution-tier sub-agents. Sub-agents inherit the
orchestrator's full tool set by default, but most execution protocols require only a small
subset. Bloated tool sets are a documented failure mode — ambiguous tool choices degrade
execution quality and consume description tokens. This library specifies how orchestration
routing tables declare minimal viable tool sets per protocol type, and what sub-agents
must do when they need a tool outside their allowlist.

---

## D. Tool Allowlist in Context Bundles

Sub-agents inherit the orchestrator's full tool set by default. Most execution protocols
require only a small subset. Bloated tool sets are a documented failure mode — ambiguous
tool choices degrade execution quality and consume description tokens.

**Rule:** Context bundle declares `tool_allowlist` — the minimal viable tool set for
the assigned execution protocol. Sub-agent is restricted to those tools.

**Orchestration protocol routing tables must declare `tool_allowlist` per route.**

Reference tool sets by protocol type:

| Protocol type | Minimal tool set |
|---|---|
| config-change | `read`, `edit`, `exec` (restricted to config path only) |
| inference-ops | `exec` (SSH only), `read` |
| crew-ops | `exec` (curl only), `read` |
| deploy | `exec` (git, build, deploy cmds), `read`, `write` |
| memory | `read`, `write` |
| atp-review | `read`, `write`, `exec` (gh pr only) |

If a sub-agent needs a tool not in its allowlist, it must report `blocked` to the
orchestrator — it cannot self-expand its tool set.

## Schema

See `schema/context-bundle.schema.json` (if applicable)
