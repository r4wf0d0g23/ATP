# Definition pinning and version discipline

Pins bind authorization to exact bytes. Protocol and variable authors use
semantic versions; any content-byte change requires a version bump. Patch is
for compatible wording/metadata, minor for additive compatible contract
changes, and major for breaking meaning or fields. CI compares bytes and
versions against the merge base.

Raw-byte SHA-256 is the identity of the authored file. Structured objects use
RFC 8785 JSON canonicalization before hashing, always omitting their own hash
field. Snapshots are written atomically to private storage and retained while
any ledger event references them. Critical revocation appends a ledger event;
it never changes an old pin or snapshot.

Legacy ID-only bundles are not reproducible. The migration adapter must resolve,
validate, snapshot, and pin them before mutation. If exact historical bytes are
unavailable, the run remains legacy/unresolved.
