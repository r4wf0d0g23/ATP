# Validator: package-id

Applies to variables containing on-chain package IDs, deployment identifiers, or similar cryptographic/deterministic identifiers.

## Validation Rules

| Check | Rule |
|---|---|
| Non-empty | Must not be empty or whitespace |
| Character set | Must match `^0x[a-f0-9]+$` (hex) or deployment-specific pattern |
| Length | Must match expected length for the chain/system (e.g., Sui: 66 chars including `0x`) |
| Uniqueness | Must not be identical to a different var's ID (IDs are unique per deployment) |
| No placeholder values | Must not contain `<`, `>`, `your-`, `example-`, `TODO`, `PLACEHOLDER` |

## Chain-Specific Rules

### Sui (Move packages)
- Format: `0x` + 64 hex chars = 66 total
- `published-at` and `original-id` must be different values for upgraded packages
- Archived/deprecated IDs must not match active IDs

### EVM (Solidity contracts)
- Format: `0x` + 40 hex chars = 42 total
- Checksum-cased addresses are preferred — validate EIP-55 checksum if available

## Anomaly Signals

| Signal | Description |
|---|---|
| ID changed from previous verification | On-change-only vars should not change without a logged deploy event |
| `published-at` equals `original-id` | Valid only for v1 (never-upgraded) packages — flag for confirmation if upgrade history exists |
| ID matches a known deprecated/archived ID | Stale reference |
| ID length is wrong for declared chain | Format mismatch |

## Staleness Interaction

`package-id` vars typically use `on-change-only` staleness policy. If `value_hash` changes between verifications without a corresponding deploy log entry, flag as `warn` with code `UNLOGGED_CHANGE` — a package ID should only change when a deploy was explicitly performed and recorded.
