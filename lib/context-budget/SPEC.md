# ATP Context Budget Library

## Purpose
Prevents pre-load from silently exceeding model context limits. Every protocol execution begins with a budget check before any var or doc is loaded.

## Size Classes

| Class | Token Range | Typical Content |
|---|---|---|
| `xs` | < 500 | Single var, no docs |
| `sm` | < 2,000 | 2-3 vars, no docs |
| `md` | < 10,000 | Several vars + 1-2 doc sections |
| `lg` | < 50,000 | Many vars + multiple full docs |
| `xl` | > 50,000 | Full system scrubs, large doc sets |

Every protocol must declare `preload_size_class` in frontmatter. This is an estimate of the **combined** token cost of all declared `requires.vars` and `requires.docs`.

## Budget Check Algorithm

```
1. Retrieve active model's context_limit from model-registry var
2. Estimate bootstrap_cost (workspace files injected at session start)
3. Estimate conversation_cost (current session history token count)
4. Estimate preload_cost from protocol's preload_size_class
5. available_headroom = context_limit - bootstrap_cost - conversation_cost - preload_cost

If available_headroom >= SOFT_FLOOR (default: 20% of context_limit):
  → status: pass

If available_headroom >= HARD_FLOOR (default: 5% of context_limit):
  → status: warn
  → Drop lowest-priority preload items until headroom >= SOFT_FLOOR
  → Priority order for dropping: docs first (lowest specificity first), then vars (on-change-only first)

If available_headroom < HARD_FLOOR:
  → status: fail
  → Halt. Surface budget failure to agent before any preload.
  → Agent must either compact session or reduce scope before proceeding.
```

## Drop Priority Order (when warn)

Items are dropped from the preload set in this order (first dropped first):
1. `requires.docs` with `section` qualifier (partial fetches dropped before full fetches)
2. `requires.docs` without section (full doc fetches)
3. `requires.vars` with `on-change-only` staleness policy
4. `requires.vars` with `ttl:Nd` staleness policy (longest TTL first)
5. `requires.vars` with `session-cache` policy
6. `requires.vars` with `always-verify` policy — **never drop these**

`always-verify` vars are never dropped. If they cannot fit in budget, status is `fail`.

## Required Protocol Field

```yaml
preload_size_class: xs | sm | md | lg | xl
```

## Schema

See `schema/budget-check.schema.json` for the full budget check result structure.
