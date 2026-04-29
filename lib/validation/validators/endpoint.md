# Validator: endpoint

Applies to variables containing URLs, API endpoints, or service addresses that must be reachable.

## Validation Rules

| Check | Rule |
|---|---|
| Format | Must match URL format: `(https?|wss?|grpc)://[host]([:/][path])?` |
| Non-placeholder | Must not contain `localhost` when a remote host is expected, `example.com`, `<your-host>` |
| Reachability | HTTP/HTTPS: GET or HEAD must return non-5xx within timeout. TCP: socket must connect within timeout. |
| TLS (HTTPS) | Certificate must not be expired. Self-signed allowed if declared in var. |
| Response shape | If `expected_response_key` is declared in var, response body must contain that key |

## Timeout Policy

| Protocol | Default Timeout |
|---|---|
| HTTP/HTTPS | 5 seconds |
| TCP | 3 seconds |
| gRPC health check | 5 seconds |

If the endpoint is behind a VPN or Tailscale, reachability may fail on first attempt — retry once after 2 seconds before marking as failed.

## Anomaly Signals

| Signal | Description |
|---|---|
| Host changed from previous verification | Endpoint migration — flag for confirmation |
| Port changed | Service may have moved |
| HTTP → HTTPS or vice versa | Protocol downgrade/upgrade — flag |
| Response time > 3x historical average | Degraded performance |
| Response status changed from 200 to 4xx | Auth or routing change |

## Non-Reachability Handling

A failed reachability check does NOT automatically invalidate the var. Some endpoints are only reachable from specific network contexts (VPN, Tailscale). When reachability fails:

1. Record as `warn` with code `ENDPOINT_UNREACHABLE`
2. Note the network context in the anomaly
3. Do NOT mark the var as failed — the format and previous value may still be valid
4. If the protocol requires the endpoint to be reachable before execution, escalate
