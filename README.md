# Agent Task Protocol (ATP)

ATP is a structural protocol layer for agent-based systems. It enforces a deterministic context lifecycle for every task that needs external knowledge, infrastructure state, or persisted state changes — so agents stop acting on stale memory, stop skipping required pre-loads, and stop forgetting to write state back. Every protocol-governed task runs through the same loop:

```
INPUT → CONTEXT DETERMINATION → CONTEXT VARIABLE VALIDATION
  → CONTEXT PRE-LOAD → INTERACTION EXECUTION
  → POST-EXECUTION CONTEXT REVIEW → OUTPUT
```

Status: spec is at **0.2.0** (active). Several supporting libraries (`execution-receipt`, `enforcement-plugin`, `bundle-schema`, `task-intake`) are still **draft**.

---

## Repository map

```
ATP/
├── SPEC.md                         # Full specification (v0.2.0, active)
├── ATP_AGENT.md                    # Per-workspace bootstrap injected at session start
│
├── schema/                         # JSON Schemas (draft-07)
│   ├── protocol.schema.json
│   ├── variable.schema.json
│   └── context-bundle.schema.json
│
├── templates/                      # Public starter content
│   ├── protocols/                  # 6 starter protocols (template / public)
│   ├── vars/                       # 2 var-file shapes (live + config)
│   └── workers/worker-config.md    # Worker schedule + cost-ratio config
│
├── lib/                            # The ATP module ecosystem (22 libs)
│   ├── orchestration/              # Two-tier model: orchestrator + executor
│   ├── task-intake/                # Gate that maps tasks → protocols
│   ├── bundle-schema/              # Context-bundle validation rules
│   ├── bundle-prompt/              # Bundle-to-prompt rendering
│   ├── jit-context/                # Just-in-time var resolution
│   ├── handoff-artifact/           # Sub-agent completion receipts
│   ├── execution-receipt/          # Audit gate for completed tasks (draft)
│   ├── outcome/                    # Sub-agent → orchestrator outcome reports
│   ├── workers/                    # T1/T2/T3 autonomous QA workers
│   ├── frontmatter/                # YAML extraction + schema validation
│   ├── validation/                 # Var-value validators (json, ssh, endpoint, …)
│   ├── auto-correct/               # In-boundary safe corrections
│   ├── checkpoint/                 # Partial-execution safety
│   ├── conflict/                   # Multi-protocol-match precedence
│   ├── context-budget/             # Pre-load token budget guard
│   ├── window-budget/              # Session-window budget tracking
│   ├── dependency/                 # Var-to-var dependency graph
│   ├── escalation/                 # Severity, routing, ack tracking
│   ├── protocol-index/             # RAG layer over protocols
│   ├── session-freshness/          # Session-cache mid-session drift detection
│   ├── tool-scope/                 # Per-protocol tool allowlists
│   └── enforcement-plugin/         # Transport-layer routing enforcement (draft)
│
├── hooks/atp/                      # OpenClaw hook implementation
│   ├── HOOK.md
│   ├── handler.ts
│   ├── hook-config.default.json
│   └── hook-config.schema.json
│
├── skills/atp/                     # Authoring & maintenance skill
│   ├── SKILL.md
│   └── references/authoring-guide.md
│
├── protocols/  vars/               # Empty by default — instance-overlay mount points
└── reports/                        # Worker output (T1/T2/T3 scan results)
```

The two top-level `protocols/` and `vars/` directories ship empty (gitignored). They exist as overlay mount points: an instance deployment writes its private protocol/var files into them locally; the public repo never carries those files.

---

## Concepts at a glance

- **Protocol** — declarative file describing a task class: which vars and docs to load, which guardrails apply, when to escalate. Lives in `templates/protocols/` (public/template) or `atp-instance/protocols/` (private). Schema: `schema/protocol.schema.json`.
- **Variable** — named cache of infrastructure or config state with a `staleness_policy` and `verify_cmd`. Agents verify before acting, never assume from memory. Schema: `schema/variable.schema.json`.
- **Tiers** — two execution roles: **orchestration** (Captain) routes tasks and aggregates state; **execution** (sub-agent) runs exactly one protocol in an isolated session. Defined in `lib/orchestration/`.
- **Context bundle** — the typed payload an orchestrator sends to a sub-agent: `protocol_id`, `var_ids[]`, `guardrails`, `task_description`, `model_class`. Schema: `schema/context-bundle.schema.json`.
- **Route decision / execution plan** — the structured routing result (`single`, `composite`, `ambiguous`, `fallback`, or `none`) and its per-step execution DAG. Schemas: `schema/route-decision.schema.json` and `schema/execution-plan.schema.json`.
- **ATP event** — a versioned, privacy-safe telemetry envelope correlated by request, decision, plan, run, and bundle IDs. Schema: `schema/atp-event.schema.json`.
- **Handoff artifact / execution receipt** — the structured receipt every sub-agent writes on completion (success, partial, or failure). Required gate: a task without a receipt is not considered complete. See `lib/execution-receipt/` and `lib/handoff-artifact/`.
- **Workers (T1 / T2 / T3)** — autonomous QA layer. T1 = scheduled scanner (`fast` model), T2 = event-driven watcher (`balanced`), T3 = deep validator (`capable`, frequency scales inversely with model cost). See `lib/workers/`.
- **Classification** — every protocol and var declares `public` (generic, ATP repo), `template` (public placeholder, ATP repo), or `private` (live values, instance-only).
- **Staleness policy** — `always-verify` | `session-cache[:Nm]` | `ttl:Nd` | `on-change-only`. Determines when `verify_cmd` runs.

---

## Quickstart

Prerequisite: an agent platform that can inject `ATP_AGENT.md` at session start (OpenClaw is the reference implementation; any platform with a bootstrap hook works).

```bash
# 1. Clone next to your agent workspace
git clone https://github.com/r4wf0d0g23/ATP atp

# 2. Symlink the bootstrap file so it loads on every session
ln -s "$(pwd)/atp/ATP_AGENT.md" /path/to/your/workspace/ATP_AGENT.md

# 3. Wire the hook (OpenClaw): point your hook system at
#    atp/hooks/atp/handler.ts
#    Schema: atp/hooks/atp/hook-config.schema.json
#    Defaults: atp/hooks/atp/hook-config.default.json

# 4. Create your private instance overlay
mkdir -p atp-instance/{protocols,vars,reports,artifacts}

# 5. Author your first protocol from a template
cp atp/templates/protocols/agent-config-change.md \
   atp-instance/protocols/my-config-change.md
$EDITOR atp-instance/protocols/my-config-change.md   # set ids, vars, dates

# 6. (Optional) Validate locally before commit
npx -p ajv-cli ajv validate \
  -s atp/schema/protocol.schema.json \
  -d atp-instance/protocols/my-config-change.md  # via frontmatter extraction
```

For a deeper authoring walk-through, see `skills/atp/SKILL.md` and `skills/atp/references/authoring-guide.md`.

---

## Why classification matters

ATP is designed so the public repo and a deployment's private operational data **cannot mix**. Three rules:

1. Anything with real hostnames, real credentials, real package IDs, or org-specific commands is `private` and lives **only** in your `atp-instance/` overlay — never in the public ATP repo.
2. Anything generic ships as `public` (universally applicable, e.g. `memory-maintenance`) or `template` (generic pattern with placeholders, e.g. `agent-config-change`).
3. Variables that hold real values are private by definition. Only structural shapes ship as `template` examples.

The included `.gitignore` enforces this: `protocols/*.md` and `vars/*.md` are ignored at the public-repo root, so an instance overlay cannot accidentally leak into upstream PRs. Workers (`lib/workers/`) additionally scan public/template files for IPs, internal hostnames, and credential-shaped strings on every push.

---

## Maturity

**Stable / active:**
- Core spec (`SPEC.md`)
- Schemas (`schema/protocol.schema.json`, `schema/variable.schema.json`, `schema/context-bundle.schema.json`)
- Templates (`templates/protocols/`, `templates/vars/`)
- OpenClaw hook (`hooks/atp/`)
- Authoring skill (`skills/atp/`)
- Worker spec (`lib/workers/`)

**Draft / evolving:**
- `lib/execution-receipt/` — audit-gate semantics for completed tasks
- `lib/enforcement-plugin/` — transport-layer routing enforcement
- `lib/bundle-schema/` — context-bundle build-time validation
- `lib/task-intake/` — pre-Captain protocol-routing gate

Draft modules ship with `SPEC.md` files marked `status: draft` in their frontmatter or top matter.

---

## Spec

`SPEC.md` is the canonical reference. It defines:

- The 6-phase canonical execution loop (`context-determination` → `output`)
- Two-tier (orchestration / execution) model
- Protocol and variable file formats
- Staleness policies
- Classification rules
- Review chain (staleness PRs, new-protocol PRs, emergency variable updates)
- Schema versioning policy (30-day grace period for new required fields)
- Library reference table

Each `lib/<name>/SPEC.md` is the authoritative reference for that layer. Read the relevant lib SPEC before implementing or modifying that layer.

---

## Contributing

PRs are welcome for `public` and `template` content. Private deployment content **must not** appear in PRs against this repo.

- New protocol PRs require a threshold-justification comment ("≥2 external sources" or "post-execution state to persist").
- Schema-breaking changes require a major version bump per `SPEC.md ## Schema Versioning`.
- Frontmatter must validate against the relevant schema; CI will reject non-conformant files.
- See `skills/atp/SKILL.md` for the authoring workflow.

A `CONTRIBUTING.md` with the full PR template and review-chain rules is forthcoming.

---

## License

MIT — see `LICENSE`.
