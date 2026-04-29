# ATP Protocol Index Library

## Purpose
Provides a vectorable, RAG-queryable index of all protocols. Replaces brittle string-match trigger classification with semantic retrieval, enabling accurate protocol selection as the library grows.

## Index Structure

The index is a flat array of `index-entry` objects (see `schema/index-entry.schema.json`). Each entry is the vectorable unit — structured for embedding, not for human reading.

Two index files exist per deployment:
- `atp/protocol-index.json` — public/template protocols only
- `atp-instance/protocol-index.json` — private instance protocols (never public)

Both are queried together at runtime, with private entries masked from any external exposure.

## Semantic Summary Guidelines

The `semantic_summary` field is the primary embedding surface. It must be:
- **Dense**: 2-3 sentences maximum, no filler
- **Distinctive**: explicitly name what distinguishes this protocol from similar ones
- **Action-oriented**: lead with what the protocol does, not what it is
- **Trigger-aware**: include the kinds of tasks and inputs that should match this protocol

**Bad** (too vague, poor embedding signal):
> "This protocol handles configuration changes. It loads relevant variables and documentation."

**Good** (dense, distinctive, trigger-aware):
> "Governs any modification to agent platform configuration files. Triggers when tasks involve changing model settings, channel configuration, credentials, or plugin state. Distinguishes from infra-ops by scope: config files only, not running services. Requires platform docs pre-load and config state var validation before any edit."

## RAG Query Specification

### Query construction
Input message → embedding → cosine similarity against all `semantic_summary` embeddings in the index.

### Matching thresholds
| Score | Action |
|---|---|
| > 0.85 | Strong match — use this protocol |
| 0.65–0.85 | Candidate — check trigger string match to confirm |
| 0.50–0.65 | Weak match — log as ambiguous, proceed without protocol or prompt agent to clarify |
| < 0.50 | No match — log as "protocol needed", proceed unprotocol'd |

### Conflict handling (multiple matches above threshold)
1. If one match > 0.85 and others < 0.75 → use the strong match
2. If multiple matches > 0.75 → apply conflict resolution (see `lib/conflict/`)
3. If unresolvable → surface both protocols to agent, let agent select

## Index Build Process

Run when: any protocol is added, modified, or deprecated.

```
1. Read all protocol frontmatter from protocols/ and templates/protocols/
2. For each protocol: extract id, name, version, classification, status,
   semantic_summary, triggers, preload_size_class, priority, requires
3. Generate embedding for semantic_summary (use deployment's embedding provider)
4. Write updated index-entry to protocol-index.json
5. Commit index update to the appropriate repo (public or instance)
```

Do NOT embed the full protocol body — only the `semantic_summary`. This keeps the index lean and embedding-focused.

## String-Match Fallback

When a RAG layer is unavailable (no embedding provider configured), the hook falls back to string-match against `triggers`. This is less accurate but functional. Log when operating in fallback mode.

## Required Protocol Field

```yaml
semantic_summary: "<2-3 sentence dense description optimized for embedding>"
preload_size_class: xs | sm | md | lg | xl
priority: 0-100   # default: 50
```
