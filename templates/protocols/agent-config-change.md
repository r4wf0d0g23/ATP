---
id: agent-config-change
name: Agent Config Change
version: 0.1.0
status: active
classification: template
# Replace with actual date when instantiating
created: "2000-01-01"
# Replace with actual date when instantiating
last_reviewed: "2000-01-01"
review_authority: deployment-owner
semantic_summary: "Governs any modification to agent platform configuration files including model settings, channel configuration, credentials, and plugin state. Triggers when tasks involve changing gateway config, model fallbacks, auth tokens, or runtime behavior settings. Distinguishes from infra-ops by scope: configuration files only, not running services."
preload_size_class: sm
priority: 50

triggers:
  - "config change"
  - "config review"
  - "agent config"
  - "gateway config"

requires:
  vars:
    - id: example-agent-config-state
      staleness_policy: session-cache
  docs:
    - url: https://<your-agent-platform-config-docs-url>

post_update:
  - example-agent-config-state

guardrails:
  - "Always fetch the relevant platform documentation before making any config edit"
  - "Validate config after edits before declaring done"
  - "Credentials must never be stored as plaintext — use SecretRef or equivalent"
  - "Never restart the gateway/runtime during an active conversation turn"

escalation:
  - "Config validation fails after edit — halt and surface to deployment owner before restarting"
  - "Credential exposure detected — rotate immediately, treat as incident"
  - "Post-edit behavior differs from expected — do not restart until root cause is understood"
checkpoint_policy:
  on_partial: write-handoff-artifact
  clean_state_definition: "Config file is valid JSON, gateway has not been restarted with partial changes"
  rollback: "Restore previous config from backup at ~/.openclaw/openclaw.json.bak"
tool_allowlist: ["read", "edit", "exec"]
---

# Agent Config Change

## Context
Any modification to agent platform configuration files. This protocol ensures the relevant platform documentation is loaded before changes are made, validation occurs after, and the config state var is updated to reflect the new known-good state.

## Pre-load Checklist
1. Load `<agent-config-state-var-id>` var — establish current baseline
2. Fetch the relevant platform config documentation for the area being changed
3. Read the current config file before making any edits

## Execution Notes
- Make one logical change at a time; validate between changes for complex edits
- For credential migrations: write to secret store first, then update config to reference it
- Know your platform's config reload behavior — some changes require restart, some hot-reload

## Post-execution Checklist
1. Run platform config validation — confirm zero errors
2. Update `<agent-config-state-var-id>` with key values changed this session
3. Log state changes to daily memory file
4. If restart required — confirm deployment owner is aware before triggering
