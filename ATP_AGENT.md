# ATP_AGENT.md — Agent Task Protocol Bootstrap

**Version:** 0.1.0

---

## What is ATP

Agent Task Protocol (ATP) is the interaction scaffold for all context-required tasks. It ensures you never act on stale infrastructure state, never skip required doc pre-loads, and always update variable state after execution.

## The Execution Loop (mandatory for all context-required interactions)

```
INPUT
  ↓ Identify which protocol applies (see dispatch table below)
CONTEXT VARIABLE VALIDATION
  ↓ For each required var: check staleness policy → verify if needed
CONTEXT PRE-LOAD
  ↓ Load all vars and docs declared by the matched protocol
INTERACTION EXECUTION
  ↓ Execute. Never assume unvalidated variable values.
POST-EXECUTION CONTEXT REVIEW
  ↓ Identify any state changes → update var files immediately
OUTPUT
```

**If no protocol matches:** proceed normally, but log the task as **protocol needed** — it is a candidate for a new protocol and must be captured in the post-execution review.

---

## Protocol Dispatch Table

This table is a **template**. Rows marked `your-*` are placeholders — replace them with your
deployment's protocols in `atp-instance/protocols/` and register their trigger strings in
`atp-instance/hook-config.json` (see `hooks/atp/HOOK.md`). The two template protocols shipped
with this repo (`memory-maintenance`, `atp-protocol-review`) are generic and ready to use.

| Task pattern | Protocol | Key vars to load |
|---|---|---|
| config changes (your infra config surface) | `your-config-change-protocol` | `your-config-state-var` |
| inference / model serving ops | `your-inference-ops-protocol` | `your-model-state-var` |
| memory update / daily log / soul review | `memory-maintenance` | — |
| inter-agent comms / secondary agent / crew ops | `your-crew-ops-protocol` | `your-crew-state-var` |
| deployment / package publish / release | `your-deploy-protocol` | `your-package-state-var` |
| ATP review / protocol staleness | `atp-protocol-review` | all vars |

Public templates: `atp/templates/protocols/` and `atp/templates/vars/`  
Instance protocols (private): `atp-instance/protocols/`  
Instance variables (private): `atp-instance/vars/`  
Hook config (triggers / state-change indicators): `atp-instance/hook-config.json` (schema in `hooks/atp/hook-config.schema.json`)  
Spec: `atp/SPEC.md`

---

## Staleness Policies (quick reference)

| Policy | Rule |
|---|---|
| `always-verify` | Run `verify_cmd` every single time. No exceptions. |
| `session-cache` | Verify once per session via `verify_cmd`, reuse within session. |
| `ttl:Nd` | Re-verify if `last_verified` older than N days. |
| `on-change-only` | Trust until a change event is explicitly logged. |

---

## Mandatory Rules

1. **Never assume infrastructure state from memory alone.** Always run `verify_cmd` for `always-verify` vars before acting.
2. **Post-execution var updates are not optional.** If a state changed, update the var file in the same session.
3. **Protocol creation threshold:** propose a new protocol when a task requires ≥2 external context sources OR has post-execution state to persist.
4. **Protocol changes go through PRs.** Direct push to `main` on the ATP repo is not permitted.
5. **Doc pre-loads are mandatory** for any protocol that declares `requires.docs`.

---

## PR Process (protocol updates)

```bash
cd <workspace>/atp
git checkout -b atp-update-YYYY-MM-DD
# make changes to protocols/ or vars/
git add -A && git commit -m "atp: [description]"
gh pr create --title "ATP Update" --body "[changes + rationale]" --reviewer <deployment-owner>
```

Primary Agent reviews staleness PRs. Deployment Owner reviews new protocol PRs.
