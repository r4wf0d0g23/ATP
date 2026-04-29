# Contributing to ATP

Thanks for considering a contribution. ATP is a public protocol-layer spec; the bar for upstream changes is "this benefits any deployment, not just mine."

## What can ship in PRs

PRs against this repo may add or change:

- **Generic protocol templates** in `templates/protocols/` (classification `public` or `template`)
- **Generic variable templates** in `templates/vars/` (classification `template`)
- **Schema** updates in `schema/` (subject to versioning rules below)
- **`SPEC.md`** clarifications, corrections, and additions
- **`lib/*/SPEC.md`** — module-level specifications
- **`hooks/`, `skills/`** — reference implementations and authoring guides
- **Repo hygiene** — README, CI, contributor docs

## What must NOT ship in PRs

- **Anything `classification: private`** — live hostnames, credentials, package IDs, org-specific commands, deployment paths. These live only in your private `atp-instance/` overlay.
- **Worker output** — `reports/*.json` is gitignored. T1/T2/T3 outputs contain runtime state and route to `atp-instance/reports/`.
- **Real-value variables** — only structural shapes with placeholder values ship here.

The `.gitignore` and worker scanners (`lib/workers/`) provide a safety net, but the contributor is the first line of defense.

---

## New protocol PRs

A new protocol is warranted when **any** of these is true:

1. The task requires ≥2 external context sources.
2. The task has post-execution state that must persist.
3. The task touches mutable infrastructure where stale memory would cause incorrect behavior.
4. The task pattern has previously failed without explicit context lifecycle.
5. The task recurs frequently enough that codifying its lifecycle pays off.

PRs adding a new protocol must include a **threshold-justification** comment in the PR description that points at one or more of the criteria above with concrete examples.

PR template (paste into the PR body):

```
### Threshold justification
Which of the 5 criteria does this protocol meet, and why?

### Classification
[ ] public  [ ] template  ([ ] private — must not be in this PR)

### Variables added or required
List any new var ids and their classification.

### Schema-breaking?
[ ] no  [ ] yes — requires major version bump per SPEC ## Schema Versioning
```

---

## Variable PRs

- New `template` variables go in `templates/vars/`.
- Real-value variables are private; never PR them upstream.
- Any change to required schema fields triggers the **30-day grace period** rule in `SPEC.md ## Schema Versioning`. T1 will open auto-migration PRs against affected protocols during the grace period.

---

## Schema PRs

- Adding a non-required field: minor version bump (e.g. 0.2.0 → 0.3.0).
- Adding a required field, removing a field, or changing a field's type: major version bump (e.g. 0.x → 1.0).
- All schema changes need a SPEC update in the same PR.

---

## Authoring workflow

The authoritative authoring guide lives at `skills/atp/SKILL.md` with reference material in `skills/atp/references/authoring-guide.md`. Read the SKILL before authoring.

Quick local validation before opening a PR:

```bash
# Validate a protocol against schema (extracts YAML frontmatter)
npx -p ajv-cli ajv validate \
  -s schema/protocol.schema.json \
  -d <(awk '/^---$/{f=!f; next} f' templates/protocols/your-file.md)

# Validate a variable
npx -p ajv-cli ajv validate \
  -s schema/variable.schema.json \
  -d <(awk '/^---$/{f=!f; next} f' templates/vars/your-file.md)
```

CI will run the same checks (forthcoming).

---

## Review chain

- **`public` protocol changes** require review from a SPEC-level maintainer.
- **`template` changes** require any maintainer review.
- **Schema changes** require explicit SPEC alignment in the same PR plus CI green.
- **Lib/SPEC additions** that introduce new first-class concepts require a SPEC `## Library Reference` table update.

---

## Reporting issues

Open a GitHub issue with:

- **Affected file(s)** (path + line)
- **Repro steps** (for behavioral issues) or **discrepancy** (for spec/doc issues)
- **Severity** — your read on `[CRITICAL] [HIGH] [MEDIUM] [LOW] [POLISH]` per the priority model in QA reports.

Security-sensitive issues (e.g. private data leaking into the public repo, credential exposure in `template` files): open a private security advisory rather than a public issue.

---

## Code of conduct

Be direct, factual, and brief. No hedging, no marketing voice, no PR theater. Bring evidence (file paths, line numbers, repro commands). Reviewers will do the same.
