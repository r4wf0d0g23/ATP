# ATP Poisoning Pattern Catalogue

Patterns that trigger `poison-suspected` status during variable validation. Any match causes the validation pipeline to halt and surface a warning before the value is injected into agent context.

## Prompt Injection Patterns

| Pattern | Description |
|---|---|
| `<!--` | HTML comment injection — may contain hidden instructions |
| `<script` | Script tag injection |
| `\n\n# ` | Markdown heading after newlines — common injection delimiter |
| `\n\nSystem:` | Fake system prompt injection |
| `\n\nUser:` | Fake user turn injection |
| `\n\nAssistant:` | Fake assistant turn injection |
| `[INST]` | LLaMA-style instruction injection |
| `<\|im_start\|>` | ChatML injection |
| `Ignore previous instructions` | Direct override attempt |
| `Disregard all prior` | Direct override attempt variant |

## Path Traversal Patterns

| Pattern | Description |
|---|---|
| `../` | Unix path traversal |
| `..\` | Windows path traversal |
| `%2e%2e` | URL-encoded traversal |
| `/etc/passwd` | Common traversal target |
| `/proc/` | Process filesystem access |

## Stale Cache Injection

Triggered when:
- `staleness_policy` is `always-verify` AND
- `value_hash` matches `previous_value_hash` exactly AND
- More than 24 hours have elapsed since `last_verified`

Signal: value is suspiciously identical across an always-verify boundary.

## Schema Poisoning

Triggered when a JSON-structured value contains keys not present in the declared schema for that variable type. Unexpected keys may be injected to add context that wasn't validated.

## Statistical Anomaly

For numeric values (counts, ports, token lengths, timestamps):
- Value outside 3σ of the last 10 recorded values → anomaly
- Value is zero when historical values are never zero → anomaly
- Value is MAX_INT or negative when always positive → anomaly

## Overflow / Truncation

| Condition | Signal |
|---|---|
| Value length = 0 | Empty response — verify_cmd may have failed silently |
| Value length > 10x expected maximum | Possible buffer overflow or garbage response |
| Value is whitespace-only | Silent failure |
| Value contains only null bytes | Binary garbage |

## Response Handling

On `poison-suspected`:
1. Do NOT inject the value into agent context
2. Log the matched pattern and the sanitized value hash
3. Surface escalation: `"Variable validation returned poison-suspected status for <var-id>. Execution halted."`
4. Require deployment owner acknowledgment before retry
