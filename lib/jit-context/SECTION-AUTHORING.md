# Context section authoring standard

Protocol compilers assign every renderable section a stable, protocol-local
`section_id`. Renaming an ID is a breaking protocol change. Sections use one of
three classes:

- `mandatory-core`: protocol identity, exact required-variable declarations,
  tool allowlist, guardrails, checkpoint policy, rollback, escalation, and
  receipt requirements. These sections are always included byte-for-byte and
  cannot be truncated, summarized, deferred, or omitted.
- `step`: instructions consumed by one execution step. They may be included
  when that step is planned, but are never summarized after pinning.
- `optional-reference`: examples or explanatory material that does not grant
  authority and does not alter safety or terminal semantics. Only this class
  may be omitted for budget.

Unknown or legacy protocols without stable section metadata use `mode=full`
and one `legacy-full-fallback` section. Variable bodies are never embedded in a
context plan; the plan refers to pinned variables and schedules JIT resolution
at the first consuming step.
