---
id: example-your-var-id
name: <Human Readable Name>
version: 0.1.0
status: active
classification: template
created: "2000-01-01"
last_verified: "2000-01-01"
verified_by: <agent-id>
staleness_policy: always-verify
validator: ssh-command
verify_cmd: |
  <command that returns current live state without modifying it>
  # Example: ssh user@host 'service-inspect-command'
source: live
---

# <Variable Name>

## Current Value

<!-- Updated by agent after each verification. -->
<!-- Format as a table or structured list matching your state shape. -->

| Field | Value | Notes |
|-------|-------|-------|
| `<field-1>` | `<value>` | |
| `<field-2>` | `<value>` | |

## Change History

| Date | Key Change | Changed By | Notes |
|------|-----------|------------|-------|
| YYYY-MM-DD | Initial record | <agent-id> | |

## Notes
- Policy is `always-verify` — run `verify_cmd` every time before acting on this value
- Never assume this value from memory; always verify from the live source
- After any change to the live system: update this file immediately in the same session
