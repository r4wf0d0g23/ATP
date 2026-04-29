# ATP Protocol Authoring Guide

This reference expands on `SKILL.md` with a complete field reference, enum values, a valid frontmatter example, and an explanation of the classification model. All protocol files must conform to `schema/protocol.schema.json` (schema version `0.1.0`).

---

## 1. Complete valid frontmatter example

```yaml
---
id: deploy-sui-package
name: Deploy Sui Move Package
version: 0.1.0
status: active
classification: public
created: "2026-01-15"
last_reviewed: "2026-04-16"
review_authority: deployment-owner
triggers:
  - "deploy move package"
  - "sui client publish"
  - "publish move module"
semantic_summary: >
  Build, publish, and register a Sui Move package on testnet or mainnet,
  updating the deployment registry and rolling forward the upgrade cap.
  Covers gas budgeting, dependency verification, and post-publish wiring.
preload_size_class: md
priority: 60
requires:
  vars:
    - id: sui-deploy-wallet
      staleness_policy: session-cache:60m
    - id: sui-network
      staleness_policy: always-verify
  docs:
    - url: "https://docs.sui.io/guides/developer/first-app/publish"
      section: "Publishing a package"
guardrails:
  - "Never publish to mainnet without explicit human confirmation"
  - "Gas budget must be explicit; no implicit defaults"
  - "Upgrade cap must be transferred to multisig within 24h"
escalation:
  - text: "Publish transaction fails twice in a row"
    severity: warn
  - text: "Gas exceeds 2× budget estimate"
    severity: critical
  - "Dependency verification skipped"
post_update:
  - update-deployment-registry
tier: execution
tool_allowlist:
  - exec
  - read
  - write
checkpoint_policy:
  on_partial: write-handoff-artifact
  clean_state_definition: >
    Either (a) no transaction submitted, or (b) publish confirmed on-chain
    and package-id persisted to the deployment registry.
  rollback: "Use upgrade cap to burn deployed package if caught pre-registry-write; otherwise none."
---
```

> **Date quoting:** Always quote ISO date strings (`"2026-01-15"`, not `2026-01-15`). Unquoted YAML dates become native date objects in some parsers and fail the schema's string + regex check.

---

## 2. Field-by-field reference

Ordered roughly as they appear in the schema. Required fields reflect `schema/protocol.schema.json` `required` array.

| Field | Type | Required | Valid values / pattern | Notes |
|---|---|---|---|---|
| `id` | string | yes | `^[a-z0-9-]+$` | Kebab-case, unique across all protocols. |
| `name` | string | yes | any | Human-readable title. |
| `version` | string | yes | `^\d+\.\d+\.\d+$` | Semantic version; bump on breaking frontmatter changes. |
| `status` | string | yes | `active` \| `draft` \| `deprecated` | Use `draft` while authoring. |
| `classification` | string | yes | `public` \| `private` \| `template` | See §3. |
| `created` | string | yes | `^\d{4}-\d{2}-\d{2}$` | ISO date. **Must be quoted.** |
| `last_reviewed` | string | yes | `^\d{4}-\d{2}-\d{2}$` | ISO date. Bump on every review. |
| `review_authority` | string | yes | any | Role or agent-id that approves PRs. |
| `triggers` | array\<string> | yes | minItems: 1 | Keyword/phrase patterns for string-match fallback. |
| `semantic_summary` | string | yes | 50–2000 chars | Dense 2–3 sentence description for embedding-based retrieval. Must be distinctive. |
| `preload_size_class` | string | yes | `xs` \| `sm` \| `md` \| `lg` \| `xl` | xs<500 tok, sm<2k, md<10k, lg<50k, xl>50k. Token cost of vars + docs combined. |
| `priority` | integer | no | 0–100, default 50 | Conflict resolution: higher wins. |
| `specificity_score` | integer | no | 0–100 | Explicit specificity override; takes precedence over computed trigger-length specificity. |
| `requires` | object | yes | `{vars?: [...], docs?: [...]}` | `additionalProperties: false`. |
| `requires.vars[].id` | string | yes (within item) | `^[a-z0-9-]+$` | Var file id. |
| `requires.vars[].staleness_policy` | string | yes (within item) | `always-verify` \| `session-cache[:<N>m]` \| `ttl:<N>d` \| `on-change-only` | E.g. `session-cache:60m`, `ttl:7d`. |
| `requires.docs[].url` | string | yes (within item) | URL | External documentation link. |
| `requires.docs[].section` | string | no | any | Section hint within the doc. |
| `post_update` | array\<string> | no | each matches `^[a-z0-9-]+$` | Protocol/worker ids to trigger after successful execution. |
| `guardrails` | array\<string> | yes | minItems: 1 | Hard rules the executor must respect. |
| `escalation` | array | yes | minItems: 1 | Each item is a string (severity defaults to `warn`) or `{text, severity}` with severity in `info` \| `warn` \| `critical`. |
| `tier` | string | no | `execution` \| `orchestration` (default `execution`) | `orchestration` = run by Captain for routing only. |
| `checkpoint_policy` | object | no (required for execution-tier protocols by convention) | `{on_partial, clean_state_definition, rollback}` | See schema for `on_partial` enum. |
| `checkpoint_policy.on_partial` | string | yes (within object) | `write-handoff-artifact` \| `commit-and-stop` \| `rollback-and-stop` | |
| `checkpoint_policy.clean_state_definition` | string | yes (within object) | ≥10 chars | What counts as a safe stopping point. |
| `checkpoint_policy.rollback` | string | yes (within object) | any | Command/steps to undo; `"none"` if not applicable. |
| `tool_allowlist` | array\<string> | no | any | Minimal viable tools for sub-agents running this protocol. |

**Top-level:** `additionalProperties: false` — no fields beyond those above are permitted.

---

## 3. The classification model

Every protocol carries a `classification` label. This determines where the file is allowed to live and who sees it.

| Value | Meaning | Storage location | Typical use |
|---|---|---|---|
| `public` | Generic, reusable pattern with no deployment-specific secrets. | ATP repo `protocols/`. | Broadly applicable workflows: schema reviews, PR etiquette, memory maintenance. |
| `template` | Public pattern with **placeholder** values meant to be copied and filled in. | ATP repo `templates/`. | Skeleton files for downstream instances to adapt. Never executed as-is. |
| `private` | Deployment-specific, contains real endpoints / IDs / wallets / hostnames. | **Instance workspace only** (e.g. `~/.openclaw/workspace/atp/protocols/`). **Never** commit to the public ATP repo. | Real-data protocols: named deployment wallets, production endpoints, specific node hostnames. |

**Rule of thumb:** If a leak of the file would reveal infrastructure or secrets, mark it `private` and keep it out of the shared repo. Workers that scan for `private-content-leaked` findings (see `worker-report.schema.json`) enforce this.

---

## 4. Grace period for newly required fields

The schema versioning policy (see `SPEC.md` → *Schema Versioning*) provides a **30-day grace period** whenever a new field is added to the `required` array. During that window:

- Validators **warn** on missing fields; they do not **fail**.
- Protocols without the new field may still load and execute.
- Authors are expected to backfill during the grace window.
- After 30 days, missing fields become hard errors.

When you see a schema change that adds a required field, check `x-schema-version` in `schema/protocol.schema.json` and the date of the change; backfill all protocols you own before the deadline.
