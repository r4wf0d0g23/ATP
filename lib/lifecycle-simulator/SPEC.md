# Lifecycle Simulator v1

The lifecycle simulator runs sanitized ATP scenarios through routing,
validation, execution, checkpoint, receipt, and outcome phases. It is a test
system, not a runtime executor.

Its adapters are deliberately incapable of production access: filesystem
writes are confined to an in-memory `/sandbox`, endpoint calls reject HTTP(S),
and the production-readonly adapter accepts only `fixture://` identifiers.
The runner uses the canonical contract hashing helper from `lib/contracts`.

Every scenario declares its expected terminal status, mutation flag, and exact
final state. A mismatch raises an assertion instead of returning a misleading
pass. Operation paths are canonicalized and resolved through the fake symlink
map; traversal, cycles, and any resolved path outside `/sandbox` are rejected.

`LifecycleResult.trace` is the simulator's internal phase trace.
`LifecycleResult.events` contains separate, schema-conformant ATP v1 event
envelopes. Partial mutation is safe only when the checkpoint policy either
rolls back byte-for-byte or records a checkpoint artifact containing the
protocol's `clean_state_definition` and exact state hash.

Run the simulator suite with:

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
```
