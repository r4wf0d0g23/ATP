# ATP Session Freshness Library

## Purpose
Prevents session-cache variables from drifting stale mid-session. A var loaded at session start is not guaranteed to be valid 4 hours later. Session freshness adds a within-session TTL layer on top of the staleness policy.

## Freshness States

| State | Condition | Action |
|---|---|---|
| `fresh` | Within TTL | Use without re-verification |
| `aging` | Past 75% of TTL | Recommend re-verification before next use |
| `stale` | Past 100% of TTL | Require re-verification before use |
| `re-verified` | Was stale, re-verify passed | Treat as fresh, reset TTL |

## Default Within-Session TTLs

| Staleness Policy | Default Session TTL |
|---|---|
| `always-verify` | N/A — verified on every use regardless |
| `session-cache` | 120 minutes |
| `ttl:Nd` | min(N days, 240 minutes) |
| `on-change-only` | No session TTL — trusted until change event |

## Custom Session TTL

Variables can override the default in two equivalent ways:

```yaml
session_ttl_minutes: 30   # override: re-verify after 30 min within session
```

Or inline in the staleness policy:

```yaml
staleness_policy: session-cache:30m   # equivalent to session_ttl_minutes: 30
```

Note: `session-cache:Nm` and `session_ttl_minutes: N` are equivalent. If both are set, the smaller value wins.

## Freshness Check During Pre-load

When a protocol's context pre-load phase loads a var:

```
1. Check freshness-state for this var in the current session
2. If status = fresh → use cached value
3. If status = aging → use cached value, log recommendation to re-verify
4. If status = stale → run verify_cmd before using
5. If var not in freshness-state (first load this session) → run verify_cmd, record loaded_at
```

## Freshness State Storage

Session freshness state is in-memory only — not persisted to disk. It resets at session start. Each session builds its own freshness picture from scratch.

Reasoning: persisting within-session state introduces synchronization complexity without meaningful benefit. The staleness policy and `last_verified` date in the var file provide the cross-session continuity.

## Long Session Handling

For sessions exceeding 4 hours (deep work sessions, autonomous agent runs):
- All `session-cache` vars with default TTL will be `stale`
- The next use of any stale var triggers re-verification automatically
- This is the correct behavior — long sessions should verify, not assume

## Required Variable Field

```yaml
session_ttl_minutes: <integer>   # optional; omit to use default from staleness policy
```

## Schema

See `schema/freshness-state.schema.json`.
