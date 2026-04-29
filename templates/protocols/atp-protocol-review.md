---
id: atp-protocol-review
name: ATP Protocol Review (Meta)
version: 0.1.0
status: active
classification: template
# Replace with actual date when instantiating
created: "2000-01-01"
# Replace with actual date when instantiating
last_reviewed: "2000-01-01"
review_authority: deployment-owner
semantic_summary: "Governs the self-maintenance loop for ATP: scrubbing all protocols and variables for staleness, drift, and inaccuracy, then opening PRs for corrections. Triggers when tasks involve reviewing ATP health, checking protocol drift, or running the periodic staleness sweep. This is the meta-protocol that keeps all other protocols accurate."
preload_size_class: lg
priority: 60

triggers:
  - "ATP review"
  - "protocol staleness"
  - "review protocols"
  - "ATP maintenance"
  - "protocol drift"

requires:
  vars: []  # Load ALL instance vars during review

post_update: []  # All vars may be updated

guardrails:
  - "Verify all vars before evaluating protocol accuracy — never evaluate drift against unverified state"
  - "Protocol changes must be submitted as PRs to the ATP repo — never direct push to main"
  - "Variable corrections can be committed directly to var files in the instance deployment"
  - "New protocol proposals require a threshold justification comment in the PR"
  - "Private content must never be included in PRs to the public ATP repo"

escalation:
  - "Multiple protocols showing drift simultaneously — may indicate a larger infrastructure change; surface to deployment owner"
  - "A var verify_cmd fails — do not mark protocol as current until root cause is understood"
checkpoint_policy:
  on_partial: commit-and-stop
  clean_state_definition: "Any opened PRs are in a consistent state; no half-written report files"
  rollback: "Close any PRs opened during this run via gh pr close"
tool_allowlist: ["read", "write", "exec"]
---

# ATP Protocol Review (Meta)

## Context
The self-maintaining loop for ATP. This protocol governs how agents review the ATP system itself for drift, staleness, and needed updates. It produces PRs for public protocol changes and direct commits for private var corrections.

## Pre-load Checklist
1. Load all instance vars (full-system scrub)
2. Read all files in both the ATP repo (`protocols/`, `templates/`) and instance deployment (`atp-instance/protocols/`, `atp-instance/vars/`)
3. Check git log for recent changes to both

## Execution Notes

### Drift detection checklist
For each protocol:
- [ ] Are `triggers` still accurate for how tasks actually arrive?
- [ ] Are `requires.vars` still the right variables?
- [ ] Are `requires.docs` URLs still valid?
- [ ] Are `guardrails` still accurate, or have new failure patterns emerged?
- [ ] Does `classification` still match — has private content crept into a public file?

For each variable:
- [ ] Run `verify_cmd` — does current value match stored?
- [ ] Is `staleness_policy` still appropriate?
- [ ] Is `last_verified` date accurate?

### PR process (public/template changes only)
```bash
cd <atp-repo-dir>
git checkout -b atp-review-YYYY-MM-DD
# make changes to public/template files only
git add -A
git commit -m "ATP review YYYY-MM-DD: [summary]"
gh pr create --title "ATP Review YYYY-MM-DD" \
  --body "[changes + rationale]" \
  --reviewer <deployment-owner>
```

### Direct commit process (private var corrections)
```bash
cd <instance-deployment-dir>
# update var files with verified current values
git add -A && git commit -m "var: update [id] - [what changed]"
```

## Post-execution Checklist
1. All var files updated with current verified values
2. PR opened for any public/template protocol changes
3. Review completion logged in daily memory file with summary
