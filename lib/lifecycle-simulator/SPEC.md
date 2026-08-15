# Lifecycle Simulator v1

The lifecycle simulator runs sanitized ATP scenarios through routing,
validation, execution, checkpoint, receipt, and outcome phases. It is a test
system, not a runtime executor.

Its adapters are deliberately incapable of production access: filesystem
writes are confined to an in-memory `/sandbox`, endpoint calls reject HTTP(S),
and the production-readonly adapter accepts only `fixture://` identifiers.
The runner uses the canonical contract hashing helper from `lib/contracts`.

Run the simulator suite with:

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
```
