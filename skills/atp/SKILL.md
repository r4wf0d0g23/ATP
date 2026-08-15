---
name: atp
description: "Agent Task Protocol (ATP) management skill. Use when: creating a new protocol, updating a variable file, reviewing protocol staleness, auditing ATP for drift, proposing protocol changes via PR, or when a task pattern recurs that lacks a protocol. Triggers on: 'create a protocol', 'update a variable', 'ATP review', 'ATP staleness', 'new protocol needed', 'protocol drift', 'review ATP', 'audit ATP', 'update var file'. NOT for: executing existing protocols (those are handled by the ATP hook and ATP_AGENT.md) or general memory maintenance (use memory-maintenance protocol)."
---

# ATP Skill

Use this skill when authoring or maintaining ATP protocols and variables — not for running them.

## Authoring a new protocol

**Threshold check first:** A new protocol is warranted when a task requires ≥2 external context sources OR has post-execution state that must be persisted. If neither condition is met, don't create a protocol.

**Create the file:**
```bash
# File: <workspace>/atp/protocols/<id>.md
# Must have valid YAML frontmatter matching schema/protocol.schema.json
```

**Required frontmatter fields** (must exactly match `schema/protocol.schema.json` `required` array):

| Field | Description |
|---|---|
| `id` | Kebab-case unique identifier. Pattern: `^[a-z0-9-]+$`. |
| `name` | Human-readable protocol name. |
| `version` | Semantic version, e.g. `0.1.0`. |
| `status` | `active` \| `draft` \| `deprecated`. |
| `classification` | `public` \| `private` \| `template`. Use `private` for deployment-specific real data, `template` for skeleton/placeholder files in the ATP repo, `public` for generic patterns. |
| `created` | ISO date string, quoted, e.g. `"2026-01-15"`. |
| `last_reviewed` | ISO date string, quoted. Bump on every review pass. |
| `review_authority` | Role identifier that approves PRs (e.g. `deployment-owner`, `primary-agent`). |
| `triggers` | Array of ≥1 keyword/pattern strings for string-match fallback. |
| `semantic_summary` | 2–3 sentence plain-language description (50–2000 chars) optimized for RAG/embedding retrieval. Must be distinctive and trigger-aware. |
| `preload_size_class` | `xs` (<500 tok) \| `sm` (<2k) \| `md` (<10k) \| `lg` (<50k) \| `xl` (>50k). Estimated total token cost of all declared vars + docs. |
| `requires` | Object with optional `vars` and `docs` arrays. |
| `guardrails` | Array of ≥1 guardrail strings. |
| `escalation` | Array of ≥1 escalation rules (string or `{text, severity}` object). |

Optional: `priority`, `specificity_score`, `post_update`, `tier`, `checkpoint_policy`, `tool_allowlist`.

See `references/authoring-guide.md` for full field reference, valid enum values, and a complete frontmatter example.

**Then update SPEC.md Protocol Index** and **ATP_AGENT.md dispatch table**.

**Submit as PR:**
```bash
cd <workspace>/atp
git checkout -b atp-new-protocol-<id>
git add protocols/<id>.md SPEC.md ATP_AGENT.md
git commit -m "atp: add <id> protocol"
gh pr create --title "New Protocol: <name>" --body "<threshold justification>" --reviewer r4wf0d0g23
```

## Updating a variable file

Variable files live in `atp/vars/<id>.md`. When updating:
1. Run the var's `verify_cmd` to get current value
2. Update `## Current Value` section
3. Update `last_verified` date in frontmatter
4. Add row to `## Change History`
5. Commit directly (var corrections don't need PR review):
```bash
cd <workspace>/atp
git add vars/<id>.md
git commit -m "var(<id>): update <what changed>"
git push origin main
```

## Staleness review

See `protocols/atp-protocol-review.md` for the full checklist. Summary:
- For each protocol: verify triggers still match, vars still correct, docs still valid
- For each var: run `verify_cmd`, check if current value matches stored value
- Open a PR for protocol changes; commit var corrections directly

## Schema validation

Protocol and variable files must conform to:
- `atp/schema/protocol.schema.json`
- `atp/schema/variable.schema.json`

See `references/authoring-guide.md` for detailed field descriptions and examples.

> **Grace period:** Newly added required fields have a 30-day grace period during which missing-field validation warns rather than fails. See `SPEC.md` → *Schema Versioning*.
