<!--
Thanks for contributing to ATP. Please fill in the sections below before
requesting review. CI will reject schema-invalid frontmatter and any file
declaring classification=private in public-shipping paths.
-->

## What is this PR?

<!-- 1–3 sentences describing the change and the gap it addresses. -->

## Type of change

- [ ] New protocol template
- [ ] New variable template
- [ ] Schema change (specify version bump below)
- [ ] SPEC update / clarification
- [ ] Library SPEC change (`lib/<name>/SPEC.md`)
- [ ] Hook / skill / repo-hygiene
- [ ] Documentation only

## Threshold justification (new protocol PRs only)

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

- [ ] `public` — generic, ATP repo
- [ ] `template` — public placeholder, ATP repo
- [ ] `private` — must NOT be in this PR. If accidentally included, please remove.

## Schema impact

- [ ] No schema change
- [ ] Minor bump (added non-required field)
- [ ] Major bump (added required field, removed field, changed type)

If a major bump: link to the SPEC ## Schema Versioning grace-period plan.

## Local validation

- [ ] Frontmatter validates against the relevant schema (`ajv validate`)
- [ ] No `classification: private` in any file shipped by this PR
- [ ] Worker output (`reports/*.json`) is not committed
