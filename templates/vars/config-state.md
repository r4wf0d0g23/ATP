---
id: example-your-var-id
name: <Human Readable Name>
version: 0.1.0
status: active
classification: template
created: "2000-01-01"
last_verified: "2000-01-01"
verified_by: <agent-id>
staleness_policy: session-cache
validator: json-config
verify_cmd: |
  <command that reads current config state>
  # Example: agent-platform config get <key>
source: config
---

# <Variable Name>

## Current Value

<!-- Updated by agent after each session verification. -->

**Host/Target:** `<hostname or service>`
**Config file/path:** `<path>`
**Platform version:** `<version>`
**Last full review:** `YYYY-MM-DD`

| Config Key | Value | Notes |
|-----------|-------|-------|
| `<key-1>` | `<value>` | |
| `<key-2>` | `<value>` | |

### Known issues / version-specific notes
<!-- Document platform-version-specific quirks or workarounds here -->

## Change History

| Date | Change | Changed By |
|------|--------|------------|
| YYYY-MM-DD | Initial record | <agent-id> |

## Notes
- Policy is `session-cache` — verify once per session via `verify_cmd`, reuse within session
- Document known platform version quirks in this file so they aren't rediscovered each session
