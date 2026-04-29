# ATP Dependency Library

## Purpose
Defines relationships between variables so load order is deterministic, circular dependencies are detected at build time, and downstream effects of verification failures are understood before execution.

## Dependency Types

| Type | Meaning |
|---|---|
| `requires` | Hard dependency. `from` var cannot be used without `to` var being verified first. If `to` fails verification, `from` cannot be loaded. |
| `enriches` | Soft dependency. `to` var improves the context of `from` but is not blocking. If `to` fails, `from` can still load with a warning. |

## Required Variable Field

```yaml
depends_on:
  - id: <var-id>
    type: requires | enriches
```

## Load Order Resolution

Load order is computed by topological sort of the dependency graph:

```
1. Build adjacency list from all vars' depends_on declarations
2. Run topological sort (Kahn's algorithm)
3. If cycle detected → build fails, surface cycle to deployment owner
4. Assign load_order integer to each node (0 = no dependencies)
5. Verify vars in load_order sequence
```

Vars at the same load_order level with no ordering dependency between them may be verified in parallel.

## Cycle Detection

Circular dependencies are invalid and must be resolved before the instance deployment is operational.

```
Example cycle: crew-state → example-inference-var → model-registry → crew-state
Resolution options:
  1. Break the cycle: determine which dependency is actually soft (enriches)
  2. Merge vars: if two vars always require each other, they may be the same var
  3. Introduce an intermediate var that both depend on
```

The dependency graph is stored in `atp-instance/dependency-graph.json` (private, generated at build time).

## Failure Propagation

When a `requires` dependency fails verification:

```
example-inference-var verification FAILS
  ↓
model-registry CANNOT load (depends_on example-inference-var via requires)
  ↓
Any protocol requiring model-registry CANNOT execute
  ↓
Budget check also FAILS (cannot estimate model context limit)
```

The dependency graph enables this propagation to be traced and surfaced as a single clear error rather than multiple confusing downstream failures.

## Schema

See `schema/dependency-graph.schema.json`.
