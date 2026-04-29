# Validator: json-config

Applies to variables where `verify_cmd` reads a configuration file or returns a JSON-structured response.

## Validation Rules

| Check | Rule |
|---|---|
| Valid JSON | Must parse without error |
| Non-empty | Parsed object/array must not be empty `{}` or `[]` unless empty is expected |
| Required keys present | All keys declared in the var's schema must be present |
| Type conformance | Values must match expected types (string, number, boolean, array, object) |
| No unexpected top-level keys | Extra keys flag schema poisoning check |

## Anomaly Signals

| Signal | Description |
|---|---|
| Required key missing | Field was present in previous verification, now absent |
| Type changed for known key | Was string, now number — likely structural change |
| Null value for non-nullable key | Key present but null |
| Deeply nested unexpected structure | New sub-objects not in declared schema |
| Array length changed by >10x | Unusual growth or truncation |

## SecretRef Handling

Config files may contain SecretRef objects `{source, provider, id}` where plaintext secrets previously existed. This is expected and valid — do not flag as anomaly. SecretRef presence where a plaintext value previously existed is a positive signal (credential hardening).

Plaintext credential value where a SecretRef previously existed IS an anomaly — flag as `warn` with code `CREDENTIAL_REGRESSION`.

## Comparison Strategy

On each validation:
1. Parse JSON
2. Extract structural fingerprint: `{key: typeof value}` map (not the values themselves)
3. Compare fingerprint against previous fingerprint
4. Flag any structural changes as anomalies for review
5. Record value hash of full parsed JSON (not the raw string)
