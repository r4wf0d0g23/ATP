# ATP Worker Library

## Purpose
Defines the three-tier autonomous agent worker architecture for continuous QA, validation, and report cleansing. Workers operate within the ATP execution loop, producing structured outputs that feed back into the protocol improvement cycle without bypassing human review gates.

---

## Worker Tier Model

| Tier | Competency | Trigger | Model Class | Cost Profile | Primary Output |
|---|---|---|---|---|---|
| T1 — Scheduled Scanner | Bulk scan, conflict prevention | Cron (high freq) | `fast` (e.g. grok-4-1-fast) | Low | PRs + `/reports` |
| T2 — Event Watcher | Event-driven diff, change detection | Webhook / git push | `balanced` (e.g. sonnet) | Medium | PRs on change |
| T3 — Deep Validator | PR validation, report cleansing | PR opened/updated | `capable` (e.g. opus) | High → decreasing | Validated PRs + cleansed `/reports` |

Each tier is defined in `tiers/t1.md`, `tiers/t2.md`, `tiers/t3.md`.

---

## Authorization Model

Workers operate with tiered autonomy. T3 may apply high-confidence corrections directly; structural protocol changes always require a PR and human merge.

| Action | T1 | T2 | T3 |
|---|---|---|---|
| Read any ATP file | ✅ | ✅ | ✅ |
| Read open PRs (conflict check) | ✅ | ✅ | ✅ |
| Write to `/reports` | ✅ | ✅ | ✅ |
| Update `last_verified` + `value_hash` in var files | ✅ on clean pass | ❌ | ✅ on validated pass |
| Open a GitHub PR | ✅ | ✅ | ✅ (for structural changes only) |
| Comment on a GitHub PR | ❌ | ✅ | ✅ |
| Apply in-boundary corrections directly | ❌ | ✅ (via auto-correct lib) | ✅ (high-confidence resolutions) |
| Apply structural protocol changes | ❌ | ❌ | ❌ (PR required) |
| Approve a GitHub PR | ❌ | ❌ | ✅ (structural PRs only — human merges) |
| Direct commit to `main` | ❌ | ❌ | ❌ |
| Modify protocol/var content directly | ❌ | ❌ | ✅ (high-confidence corrections with reasoning log) |
| Cleanse `/reports` (dedup, remove stale) | ❌ | ❌ | ✅ |
| Capture training pairs to `/corrections` | ❌ | ❌ | ✅ (every correction — sanitized, append-only) |
| Trigger escalation to Raw | ✅ (CRITICAL only) | ✅ (CRITICAL only) | ✅ (unresolvable only, with full reasoning attached) |

> **Escalation policy:** Raw receives escalations only when T3 has exhausted its reasoning and cannot determine the correct resolution. Every escalation to Raw must include T3's full reasoning chain — not a raw problem statement. Raw makes a decision, not a diagnosis.

---

## Output Routing

```
T1 (Cron scan)
  ├── PRs → ATP repo (protocol/var drift, schema violations, missing fields)
  └── Reports → atp-instance/reports/YYYY-MM-DD-t1-scan.json

T2 (Event watcher)
  └── PRs → ATP repo (on-change: schema violations, private content leakage, index drift)

T3 (Deep validator)
  ├── High-confidence corrections → applied directly (reasoning logged to report)
  ├── Low-confidence findings → PR opened with full reasoning attached
  ├── PR review comments → GitHub (block or approve)
  ├── Cleansed reports → atp-instance/reports/ (removes duplicates, synthesizes anomalies)
  ├── Training pairs → atp-instance/corrections/ (every correction, sanitized, append-only — future fine-tune corpus)
  └── Escalations to Raw → only when T3 reasoning exhausted, full reasoning pre-attached
```

---

## Cost-Frequency Scaling Law

T3 frequency is governed by the `cost_efficiency_ratio` variable:

```
T3_frequency = base_frequency × (1 / cost_efficiency_ratio)

cost_efficiency_ratio = current_t3_model_cost_per_mtok / baseline_t3_model_cost_per_mtok
```

| Ratio | Meaning | T3 Frequency Multiplier |
|---|---|---|
| 1.0 | Same cost as baseline | 1× (base) |
| 0.5 | Half cost | 2× |
| 0.25 | Quarter cost | 4× |
| 0.1 | 10× cheaper | 10× |

The `cost_efficiency_ratio` is stored in `atp-instance/vars/worker-config.md` and updated when model pricing changes. The T3 cron schedule is recalculated from this ratio automatically.

The frequency multiplier is capped at `MAX_FREQUENCY_MULTIPLIER` (default: 20). This prevents unbounded schedule acceleration as models approach zero cost:

```
effective_multiplier = min(1 / cost_efficiency_ratio, MAX_FREQUENCY_MULTIPLIER)
```

`MAX_FREQUENCY_MULTIPLIER` is configurable in worker-config and defaults to 20.
At 20× the base weekly schedule, T3 runs approximately every 8 hours — beyond this,
additional frequency gains are diminishing returns and create excessive PR noise.

This ensures T3 progressively absorbs more of the validation workload as capable models become cheaper, without requiring manual reconfiguration.

---

## Worker Session Architecture

### T1 — Isolated cron session
- `--session isolated` per run
- No persistent session state
- Fresh context each execution
- Output delivered to ops-console channel

### T2 — Webhook-triggered isolated session
- Triggered by `POST /hooks/agent` on git push
- `--session isolated` per trigger event
- Receives changed file list as input context
- Output: PR opened in ATP repo

### T3 — Persistent named session
- `--session session:atp-t3-validator`
- Accumulates PR review history across runs
- Enables cross-PR pattern detection ("this type of error keeps appearing")
- Session reset monthly or on demand

---

## Report Structure

All worker reports written to `atp-instance/reports/`. T3 cleanses this directory.

Report naming:
```
YYYY-MM-DD-t1-scan-<slug>.json       # T1 scheduled scan
YYYY-MM-DD-t2-change-<slug>.json     # T2 event-triggered
YYYY-MM-DD-t3-validation-<slug>.json # T3 PR validation
YYYY-MM-DD-t3-cleanse.json           # T3 cleanse run summary
```

See `schema/worker-report.schema.json` for report structure.

---

## Worker Job Spec

Each worker execution is governed by a job spec. See `schema/worker-job.schema.json`.

---

## Conflict Prevention (T1 responsibility)

Before T1 opens any PR, it reads all currently open PRs in the ATP repo and checks for:
1. **Content conflict** — does a proposed change touch the same file as an open PR?
2. **Semantic conflict** — does the proposed change contradict or duplicate an open PR's intent?
3. **Staleness** — is there an open PR that already addresses the issue T1 found?

If any conflict is detected:
- T1 comments on the existing PR instead of opening a new one
- T1 notes the conflict in its report
- T1 does NOT open a duplicate PR

---

## Progression Path

```
Today:    T1 runs daily, T2 runs on push, T3 runs weekly (high cost)
          ↓
Near term: T3 cost drops 50% → T3 runs 2× weekly
          ↓
Mid term:  T3 cost drops 75% → T3 runs daily, absorbs some T1 work
          ↓
Long term: T3 cost drops 90% → T3 runs per-PR (full CI gate)
           T1 remains for bulk scans (different competency, not replaced)
           T2 remains for event-driven (different trigger, not replaced)
```

T1 and T2 are never made redundant by T3 improvement — they serve different trigger models. T3 frequency increases; T1 and T2 remain at baseline.
