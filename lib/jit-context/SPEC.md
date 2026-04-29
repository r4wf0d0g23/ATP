# JIT Context Library

## Purpose

Defines the just-in-time variable resolution pattern for execution-tier sub-agents.
Context bundles carry var IDs as references rather than pre-loaded content, preventing
the stale var problem and avoiding loading content the sub-agent may never need.
This library specifies the resolution contract, the exception for session-cached vars,
and how failures during resolution must be handled.

---

## B. Just-in-Time Var Resolution

Context bundles carry var IDs as references, not pre-loaded content. Sub-agents resolve
vars JIT — only when the execution loop actually reaches the variable validation step for
that var, and only via `verify_cmd`.

**Why:** Pre-loading all declared vars before execution begins loads content the sub-agent
may never need (e.g., `atp-protocol-review` declares all 5 vars, but a partial scan may
only touch 2 protocols that require 1 var). Pre-loading is also the source of the stale
var problem — a var loaded at bundle receipt may be stale by the time it's used.

**Rule:** Context bundle `var_ids[]` is a reference list. The sub-agent:
1. Receives `var_ids[]` — knows which vars are in scope
2. Does NOT pre-load them on bundle receipt
3. Loads each var via `verify_cmd` only when the execution loop reaches it
4. If `verify_cmd` fails → halt that var's protocol step, report failure, do not proceed
   with stale state

**Exception:** `staleness_policy: session-cache` vars may be pre-loaded if previously
verified in the same session by the orchestrator — pass the cached value in
`orchestrator_context.cached_vars` rather than re-running `verify_cmd`.

## Schema

See `schema/context-bundle.schema.json` (if applicable)
