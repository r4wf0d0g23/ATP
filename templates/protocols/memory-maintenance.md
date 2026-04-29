---
id: memory-maintenance
name: Memory Maintenance
version: 0.1.0
status: active
classification: public
# Replace with actual date when instantiating
created: "2000-01-01"
# Replace with actual date when instantiating
last_reviewed: "2000-01-01"
review_authority: deployment-owner
semantic_summary: "Governs structured memory operations including daily log writes, long-term memory promotions, and variable file updates after state changes. Triggers when tasks involve writing session context to disk, reviewing memory for promotions, or running maintenance cycles. Applies universally with no deployment-specific values."
preload_size_class: xs
priority: 40

triggers:
  - "memory update"
  - "memory review"
  - "daily log"
  - "memory maintenance"
  - "morning brief"
  - "promote to long-term"

requires:
  vars: []
  docs: []

post_update: []

guardrails:
  - "Daily memory log must be written to a date-stamped file — never rely on mental notes"
  - "Infrastructure variable changes must be written to both the daily log AND the relevant var file in the same session"
  - "Long-term memory promotions must be curated — raw logs go in daily files, only durable facts go in long-term memory"
  - "Stale entries in long-term memory must be corrected when discovered — do not defer"
  - "Post-restart open tasks must be scanned and resolved status logged at the start of the next session"

escalation:
  - "Long-term memory file exceeds manageable size — raise for pruning review with deployment owner before adding more"
  - "Conflicting facts found between long-term memory and a var file — surface conflict before proceeding"
checkpoint_policy:
  on_partial: write-handoff-artifact
  clean_state_definition: "All file writes are complete and consistent; no partial MEMORY.md edits"
  rollback: "git checkout -- memory/ MEMORY.md to restore pre-execution state"
tool_allowlist: ["read", "write"]
---

# Memory Maintenance

## Context
Structured memory operations: daily log writes, long-term memory promotions, and var file updates. This protocol is `public` because the pattern applies generically across any agent deployment — it contains no deployment-specific values.

## Pre-load Checklist
1. Read today's daily memory log — understand current session state
2. Read yesterday's log if today's is empty or missing
3. For full maintenance: read relevant sections of long-term memory

## Execution Notes

### Daily log structure (recommended)
```markdown
## STATE_CHANGES      — what was changed, where, why
## KEY_FACTS          — IPs, IDs, endpoints, versions discovered
## DECISIONS          — decisions made with rationale
## OPEN_TASKS         — [ ] started but incomplete items
## LESSONS            — behavior changes for future sessions
```

### Long-term memory promotion criteria
Promote when a fact will be needed across multiple future sessions, an infrastructure state has been verified and is durable, a lesson learned should change future behavior permanently, or a milestone defines current project state.

Do NOT promote session-specific operational details or temporary states — those go in daily logs. Infrastructure state with a `verify_cmd` belongs in a var file, not long-term memory.

### Var file updates (mandatory)
When any infrastructure state changes, update the corresponding var file immediately — not at end of session, not in the next session. Same session, same turn if possible.

## Post-execution Checklist
1. Daily log written for this session
2. Any var files that needed updating were updated
3. If long-term memory was modified — confirm no stale entries remain in modified sections
