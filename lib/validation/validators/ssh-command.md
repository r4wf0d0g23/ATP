# Validator: ssh-command

Applies to variables where `verify_cmd` executes a command over SSH and returns structured or semi-structured output.

## Expected Input
Raw stdout from an SSH command execution.

## Validation Rules

| Check | Rule |
|---|---|
| Non-empty | Output must not be empty or whitespace-only |
| No SSH error strings | Must not contain: `Connection refused`, `No route to host`, `Permission denied`, `Host key verification failed`, `ssh: connect to host` |
| No shell error strings | Must not contain: `command not found`, `No such file or directory`, `Permission denied` at line start |
| Exit signal | If exit code is available, must be 0 |
| Encoding | Must be valid UTF-8 |

## Format Variants

### JSON output (e.g., docker inspect)
```
Expected: valid JSON array or object
Anomaly: valid JSON but top-level type changed from expected (was array, now object)
```

### Key-value output (e.g., systemctl status)
```
Expected: lines of "Key: Value" or "KEY=VALUE"
Anomaly: expected keys absent from output
```

### Plain text list (e.g., docker ps)
```
Expected: one item per line, consistent column structure
Anomaly: zero lines when at least one is expected
```

## Anomaly Signals

| Signal | Description |
|---|---|
| Output shorter than 10 chars | Likely truncated or silent failure |
| Contains `(none)` or `null` where value expected | Empty state |
| JSON key count changed by >50% from previous | Structural drift |
| Hostname in output doesn't match expected host | Wrong endpoint |

## Post-validation

After passing validation, extract the specific value needed and record its SHA-256 hash. Do not store raw SSH output in the var file — store only the extracted, structured value.
