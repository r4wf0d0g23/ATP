# Window Budget Library

## Purpose

Governs the orchestrator's context window size over the course of a session. Context rot
applies to orchestrator sessions just as it does to execution sessions — accumulated
outcome reports and loaded vars degrade routing accuracy over time. This library defines
the ceiling, the prune-after-write rule, and the budget class used by
`lib/context-budget/` to enforce it.

---

## A. Orchestrator Window Budget Rule

Context rot applies to the orchestrator session too. Every outcome report and loaded
var consumes attention budget that degrades routing accuracy over time. The orchestrator
window must stay roughly constant size regardless of how many tasks have been routed.

**Rule:** After each routing cycle completes:
1. Read sub-agent outcome report
2. Extract state changes → write to var files
3. **Drop the report from working context** — do not carry it forward
4. Do not accumulate outcome reports in the orchestrator session

**Target:** Orchestrator active context ≤ `preload_size_class: md` (8k tokens) at any point.
This means: topology vars + current task + one outcome report at a time. Never all of them.

**Implementation note for `lib/context-budget/`:** Orchestrator sessions should set
`budget_class: orchestration` which enforces the md ceiling on active working context.
Outcome reports are explicitly excluded from the budget calculation after the write-back
step completes.

## Schema

See `schema/context-bundle.schema.json` (if applicable)
