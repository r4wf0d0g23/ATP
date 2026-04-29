# ATP Conflict Library

## Purpose
Defines precedence rules when multiple protocols match the same input above the retrieval confidence threshold. Prevents arbitrary first-match-wins behavior as the protocol library grows.

## Default Precedence Algorithm

When multiple protocols score above the match threshold, apply in order:

```
1. EXPLICIT CONFLICT RULE
   Check conflict-rules.json in instance deployment.
   If a rule exists for this pair → apply it. Done.

2. PRIORITY FIELD
   Compare priority values (0-100, default 50).
   Higher priority wins. If equal → continue to step 3.

3. TRIGGER SPECIFICITY
   Compare the length of the matched trigger string. Longer trigger string = more specific match.
   If the match was via semantic retrieval: lower embedding distance from query = more specific.
   If still tied → continue to step 4.
   
   Note: A protocol may declare an explicit `specificity_score` (0-100) in its frontmatter to
   override this computed heuristic. Higher score = more specific. Takes precedence over
   trigger-length comparison when present on either protocol.

4. CLASSIFICATION SPECIFICITY
   private > template > public
   (Instance-specific protocols take precedence over generic templates)

5. AMBIGUOUS — SURFACE TO AGENT
   If all tiebreakers are equal, surface both matches to the agent with scores.
   Agent selects. Record selection as a new conflict rule for future use.
```

## Conflict Rule File

Instance deployments maintain `atp-instance/conflict-rules.json`:

```json
{
  "rules": [
    {
      "id": "cr-001",
      "protocol_a": "example-config-protocol",
      "protocol_b": "example-inference-protocol",
      "resolution": "manual",
      "winner": "example-config-protocol",
      "context_conditions": ["message contains 'inference config' or 'system config'"],
      "rationale": "Config protocol is more specific when both inference and system config are mentioned together",
      "created": "YYYY-MM-DD"
    }
  ]
}
```

## Conflict Detection

Conflicts are detected at index build time and flagged when two protocols have:
- Overlapping trigger strings (substring match between any two triggers), AND
- Similar `semantic_summary` cosine similarity > 0.80

Detected conflicts are logged to `atp-instance/conflict-candidates.json` for review. They are not automatically created as conflict rules — human review required.

## Required Protocol Field

```yaml
priority: 0-100   # default: 50. Higher wins on conflict.
```

## Schema

See `schema/conflict-rule.schema.json`.
