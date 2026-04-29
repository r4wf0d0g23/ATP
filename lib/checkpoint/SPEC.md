# Checkpoint Library

## Purpose

Defines checkpoint policies for execution protocols, governing how partial execution
should be handled when a sub-agent times out or cannot complete its full execution loop.
Without a checkpoint policy, timed-out sub-agents leave infrastructure in unknown
intermediate states with no recovery path. This library specifies the required frontmatter
field, the three policy values, and the trigger rule for when sub-agents must apply their
checkpoint policy before attempting to rush remaining steps.

---

## E. Checkpoint Policy in Execution Protocols

Execution protocols must declare how partial execution should be handled. Without a
checkpoint policy, a timed-out sub-agent leaves infrastructure in an unknown intermediate
state with no recovery path.

**Required field in execution protocol frontmatter:**
```yaml
checkpoint_policy:
  on_partial: write-handoff-artifact | commit-and-stop | rollback-and-stop
  clean_state_definition: "<what constitutes a safe stopping point>"
  rollback: "<command or steps to undo partial execution>"
```

**Policy values:**
- `write-handoff-artifact`: write the handoff artifact with `outcome: partial` and stop.
  Use when partial state is recoverable and the next run can resume from it.
- `commit-and-stop`: commit any file/git changes made so far, write handoff artifact, stop.
  Use for deploy-type protocols where partial commits are better than no record.
- `rollback-and-stop`: undo all changes made during this execution, write handoff artifact
  with `outcome: failed`, stop. Use when partial state is worse than pre-execution state.

**Sub-agent checkpoint trigger:** If `timeout_seconds - elapsed > 30s` and the sub-agent
detects it cannot complete the full execution loop, it must apply `checkpoint_policy`
immediately rather than attempting to rush the remaining steps.

## Schema

See `lib/execution-receipt/schema/handoff-artifact.schema.json` (if applicable)
