# lib/frontmatter — YAML Frontmatter Extraction and Validation

## Purpose
Specifies how YAML frontmatter in ATP protocol and variable files (.md) is extracted, parsed, and validated against JSON Schemas. This is the bridge between Markdown-based ATP files and the JSON Schema validation layer.

## Extraction Algorithm
1. Read the file as UTF-8 text
2. Check that the file starts with `---` on the first line
3. Find the closing `---` delimiter (first occurrence after line 1)
4. Extract the content between the two `---` delimiters as YAML text
5. Parse the YAML text into an object
6. If parsing fails → emit a parse-result with status: parse-error and code FRONTMATTER_PARSE_ERROR
7. Determine which schema to validate against: protocol files → schema/protocol.schema.json, variable files → schema/variable.schema.json
8. Validate the parsed object against the appropriate schema
9. Emit a frontmatter-parse-result with all findings

## Schema Mapping
All frontmatter fields map 1:1 to their corresponding JSON Schema properties. No transformation is applied. Field names must match exactly (case-sensitive).

## Template Relaxation
Files with `classification: template` in their frontmatter receive relaxed validation:
- Date fields (`created`, `last_reviewed`, etc.): pattern validation emits `warn` severity instead of `critical`. The canonical placeholder date is `2000-01-01`.
- Required fields containing obvious placeholders (e.g., `<replace-me>`, `PLACEHOLDER`, empty string): emit `warn` instead of `critical`
- Missing optional fields: emit `info` instead of `warn`

The canonical placeholder date for template files is `2000-01-01`. All template files should use this value.

## Error Codes
| Code | Meaning |
|------|---------|
| FRONTMATTER_PARSE_ERROR | YAML could not be parsed |
| FRONTMATTER_MISSING | File has no --- delimiter |
| SCHEMA_VALIDATION_FAIL | Parsed object fails JSON Schema validation |
| TEMPLATE_PLACEHOLDER_WARN | Template file has placeholder value (warn only) |

## Output
Each extraction emits a `frontmatter-parse-result` object (see schema/frontmatter-parse-result.schema.json).
