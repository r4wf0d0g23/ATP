---
name: atp
description: "Agent Task Protocol execution loop. Implements the ATP context lifecycle for every interaction: context determination, variable validation, pre-load, and post-execution review."
metadata:
  { "openclaw": { "emoji": "🔗", "events": ["agent:bootstrap", "message:preprocessed", "message:sent"], "requires": { "bins": ["node"] } } }
---

# ATP Hook

Implements the Agent Task Protocol (ATP) execution loop at the OpenClaw hook layer.

## What it does

### agent:bootstrap
- Injects `ATP_AGENT.md` into `bootstrapFiles` if not already present
- Loads the protocol dispatch table from `atp/SPEC.md`

### message:preprocessed
- Classifies the incoming message against protocol trigger patterns
- If a protocol matches: logs the matched protocol to context
- Enriches `bodyForAgent` with a brief ATP context note identifying the active protocol

### message:sent
- Scans the outbound message for indicators of state changes
- If infrastructure-relevant keywords detected: appends a post-execution var review reminder to internal state

## Configuration

The hook loads its trigger configuration at runtime. Configuration is resolved in this order:

1. **Instance override** — `<workspace>/atp-instance/hook-config.json`
   Place `atp-instance/hook-config.json` in your workspace to override triggers for your deployment. The workspace path comes from `event.context.workspaceDir`, then `process.env.OPENCLAW_WORKSPACE`, then `process.cwd()` as a last resort.
2. **Built-in default** — `hooks/atp/hook-config.default.json` (co-located with this hook)
   Falls back to the default config if no instance override is present. Ships with the two template protocols only (`memory-maintenance`, `atp-protocol-review`) plus a small set of deployment-neutral state-change indicators.
3. **Hard-coded minimal fallback** — used only if both JSON files fail to load or fail schema validation.

The config is loaded once per process and cached. Invalid JSON or schema mismatches are logged and skipped — the hook will silently fall through to the next source rather than breaking.

### Config schema

See `hook-config.schema.json` for the formal JSON Schema definition. Minimal shape:

```json
{
  "protocol_triggers": {
    "<protocol-id>": ["trigger string", "another trigger"]
  },
  "state_change_indicators": [
    "string that, if seen in an outbound message, hints at a state change"
  ]
}
```

- `protocol_triggers` keys must match a protocol id that exists (or that you plan to add) under `atp-instance/protocols/` or `atp/protocols/`.
- Matching is case-insensitive substring match.
- `state_change_indicators` are logged post-execution as a nudge to review variables.

### Example instance override

```json
{
  "protocol_triggers": {
    "memory-maintenance": ["memory update", "daily log"],
    "my-deploy-protocol": ["deploy cluster", "kubectl rollout"]
  },
  "state_change_indicators": ["kubectl apply", "terraform apply", "helm upgrade"]
}
```

## Notes

The hook operates in advisory mode — it enriches context and logs protocol matches but does not block execution. The agent is responsible for following the protocol's pre-load and post-execution checklists as directed by `ATP_AGENT.md`.
