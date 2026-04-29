# Bundle Prompt Library

## Purpose
Defines the canonical structure for prompts passed to execution-tier sub-agents via context bundles. Based on Anthropic prompting best practices: long-form data at top, task/query always last (improves response quality up to 30%).

## Bundle Prompt Structure

Canonical XML structure for all context bundles:

```xml
<context_bundle>
  <role>[sub-agent role declaration tuned to protocol]</role>
  <vars>
    [var content loaded JIT — inserted here when verified]
  </vars>
  <docs>
    [any required docs declared by the protocol]
  </docs>
  <guardrails>
    [guardrails from the matched protocol + orchestrator additions]
  </guardrails>
  <task>
    [task_description — ALWAYS LAST]
  </task>
</context_bundle>
```

## Role Declaration per Protocol

| Protocol | Role string |
|---|---|
| example-config-protocol | "You are a configuration operator. You make precise, validated changes to gateway configuration files." |
| example-inference-protocol | "You are an inference infrastructure operator. You manage vLLM containers and verify serve parameters via live inspection." |
| crew-ops | "You are a crew communications relay. You route messages between crew agents via the established gateway invoke path." |
| crew-peering | "You are a crew onboarding specialist. You establish bidirectional gateway peering between new agents and the crew." |
| example-deploy-protocol | "You are a deployment operator. You publish Move packages and deploy the dApp to GitHub Pages." |
| memory-maintenance | "You are a memory maintenance agent. You write accurate session context to disk and promote durable facts to long-term memory." |
| atp-protocol-review | "You are an ATP quality auditor. You scan protocols and vars for schema violations, staleness, and drift." |

## Long-Context Ordering Rule

Per Anthropic docs: queries at the end improve response quality by up to 30% for complex inputs.
Rule: the `<task>` tag MUST be the last element. All context (vars, docs, guardrails) precedes it.

## Multi-Context Window Cold-Start

Include this block in bundle prompts for stateful infrastructure protocols:

```
<cold_start>
1. Read handoff artifacts from atp-instance/artifacts/ — find most recent for this protocol_id
2. If found: orient from state_after and next_action fields
3. If not found: proceed from vars only
4. Do not ask the orchestrator for context — reconstruct from artifacts and vars
</cold_start>
```

## Few-Shot Examples

For protocols where output format matters (atp-protocol-review, memory-maintenance), the orchestrator injects 1-2 canonical examples wrapped in `<example>` tags from the protocol's `examples/` directory if present.

## Anti-Patterns

- Do NOT pre-load all vars into the bundle prompt before JIT resolution
- Do NOT put the task description first — context rot causes model to focus on task before reading context
- Do NOT include more than one protocol's guardrails in a single bundle
- Do NOT use vague role strings — always use protocol-specific roles
