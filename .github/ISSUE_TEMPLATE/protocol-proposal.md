---
name: Protocol proposal
about: Propose a new protocol for inclusion in the public repo
labels: protocol-proposal
---

## Proposed protocol id

<!-- e.g. `cloud-deploy`, `secrets-rotation` -->

## Threshold justification

<!--
Per SPEC ## Protocol Definition, a new protocol is warranted when ANY of:
1. Task requires ≥2 external context sources
2. Task has post-execution state that must persist
3. Task touches mutable infrastructure where stale memory causes incorrect behavior
4. Task pattern has previously failed without explicit context lifecycle
5. Task recurs frequently enough that codifying its lifecycle pays off

Quote which criteria apply and why. Concrete examples preferred.
-->

## Classification

- [ ] `public` — every adopter would use this verbatim
- [ ] `template` — generic shape with placeholders

## Sketch

<!-- Frontmatter sketch (not required to be complete). -->

```yaml
id: my-protocol-id
name: ...
classification: ...
triggers:
  - ...
requires:
  vars: []
  docs: []
guardrails:
  - ...
```

## Why upstream rather than instance-only?

<!--
What makes this protocol generic enough to ship in the public repo, vs.
keeping it in your private atp-instance/ overlay?
-->
