"""Cross-document invariants that JSON Schema draft-07 cannot express.

The functions return stable machine-readable error codes. They do not read the
filesystem, execute validators, or mutate runtime state.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re


TERMINAL = {"completed", "failed", "violated"}
SECRET_KEY = re.compile(r"(?i)(^|[_-])(api[_-]?key|access[_-]?token|auth[_-]?token|password|passwd|private[_-]?key|secret|authorization|cookie)$")
SECRET_VALUE = re.compile(
    r"(?i)(-----BEGIN [A-Z ]*PRIVATE KEY-----|\bBearer\s+[A-Za-z0-9._~+/=-]{8,}|\bsk-[A-Za-z0-9_-]{12,}|(?:session|discord|slack):[^\s]{8,})"
)


def canonical_sha256(value: object) -> str:
    """Hash contract objects whose values are JSON strings/integers/booleans.

    Contract producers use RFC 8785. ATP pin objects contain no floats, so
    sorted compact UTF-8 JSON is byte-identical to RFC 8785 for this domain.
    """
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def validate_bundle_receipt(bundle: dict, receipt: dict, attestations: list[dict]) -> list[str]:
    errors: list[str] = []
    bundle_for_hash = {k: v for k, v in bundle.items() if k != "bundle_sha256"}
    if bundle.get("bundle_sha256") != canonical_sha256(bundle_for_hash):
        errors.append("bundle-hash-mismatch")
    receipt_for_hash = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
    if receipt.get("receipt_sha256") != canonical_sha256(receipt_for_hash):
        errors.append("receipt-hash-mismatch")
    for field in ("decision_id", "run_id", "plan_id", "bundle_id", "bundle_sha256", "protocol_id"):
        if bundle.get(field) != receipt.get(field):
            errors.append(f"correlation-mismatch:{field}")
    if bundle.get("protocol_id") != bundle.get("protocol_pin", {}).get("id"):
        errors.append("bundle-protocol-pin-id-mismatch")
    if receipt.get("protocol_id") != receipt.get("protocol_pin", {}).get("id"):
        errors.append("receipt-protocol-pin-id-mismatch")
    if bundle.get("protocol_pin") != receipt.get("protocol_pin"):
        errors.append("protocol-pin-mismatch")

    bundle_pins = bundle.get("variable_pins", [])
    receipt_pins = receipt.get("variable_pins", [])
    if bundle_pins != receipt_pins:
        errors.append("variable-pins-mismatch")
    pin_ids = [p.get("id") for p in bundle_pins]
    if pin_ids != sorted(pin_ids) or len(pin_ids) != len(set(pin_ids)):
        errors.append("variable-pins-not-unique-sorted")

    by_id = {a.get("attestation_id"): a for a in attestations}
    if len(attestations) != len(bundle_pins) or len(by_id) != len(attestations):
        errors.append("attestation-cardinality-mismatch")
    for pin in bundle_pins:
        att = by_id.get(pin.get("attestation_id"))
        if not att:
            errors.append(f"attestation-missing:{pin.get('id')}")
            continue
        expected = (pin.get("id"), pin.get("version"), pin.get("content_sha256"), pin.get("validator_sha256"))
        actual = (att.get("var_id"), att.get("var_version"), att.get("var_sha256"), att.get("validator_sha256"))
        if expected != actual:
            errors.append(f"attestation-pin-mismatch:{pin.get('id')}")
    return errors


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def validate_ledger(events: list[dict], now: datetime | None = None) -> list[str]:
    errors: list[str] = []
    now = now or datetime.now(timezone.utc)
    pending = [e for e in events if e.get("event_type") == "pending"]
    if len(pending) != 1:
        errors.append("ledger-pending-cardinality")

    seen_ids: dict[str, str] = {}
    seen_sequences: dict[int, str] = {}
    ordered = sorted(events, key=lambda e: e.get("sequence", -1))
    if ordered:
        correlation = tuple(ordered[0].get(k) for k in ("decision_id", "run_id", "plan_id", "bundle_id", "bundle_sha256", "protocol_id"))
        if any(tuple(e.get(k) for k in ("decision_id", "run_id", "plan_id", "bundle_id", "bundle_sha256", "protocol_id")) != correlation for e in ordered[1:]):
            errors.append("ledger-correlation-mismatch")
    for event in events:
        encoded = json.dumps(event, sort_keys=True, separators=(",", ":"))
        event_id, sequence = event.get("event_id"), event.get("sequence")
        if event_id in seen_ids and seen_ids[event_id] != encoded:
            errors.append("ledger-duplicate-id-tamper")
        elif event_id in seen_ids:
            errors.append("ledger-duplicate-event")
        seen_ids[event_id] = encoded
        if sequence in seen_sequences and seen_sequences[sequence] != encoded:
            errors.append("ledger-duplicate-sequence-tamper")
        elif sequence in seen_sequences:
            errors.append("ledger-duplicate-event")
        seen_sequences[sequence] = encoded
        event_for_hash = {k: v for k, v in event.items() if k != "event_sha256"}
        if event.get("event_sha256") != canonical_sha256(event_for_hash):
            errors.append(f"ledger-event-hash-mismatch:{sequence}")

    if [e.get("sequence") for e in ordered] != list(range(len(ordered))):
        errors.append("ledger-sequence-not-contiguous")
    for index, event in enumerate(ordered):
        expected = None if index == 0 else ordered[index - 1].get("event_sha256")
        if event.get("previous_event_sha256") != expected:
            errors.append(f"ledger-previous-hash-mismatch:{index}")

    submitted = {(e.get("receipt_id"), e.get("receipt_sha256")) for e in ordered if e.get("event_type") == "receipt-submitted"}
    terminal_indexes = [i for i, e in enumerate(ordered) if e.get("event_type") in TERMINAL]
    if len(terminal_indexes) > 1:
        errors.append("ledger-multiple-terminal-events")
    if terminal_indexes and terminal_indexes[0] != len(ordered) - 1:
        errors.append("ledger-event-after-terminal")
    for event in ordered:
        if event.get("event_type") == "completed" and (event.get("receipt_id"), event.get("receipt_sha256")) not in submitted:
            errors.append("ledger-completed-without-submitted-receipt")
        if event.get("event_type") == "bypass-granted":
            try:
                expiry = _parse_time(event["bypass_expires_at"])
                occurred = _parse_time(event["occurred_at"])
                if expiry <= occurred or expiry <= now:
                    errors.append("ledger-bypass-expired")
            except (KeyError, TypeError, ValueError):
                errors.append("ledger-bypass-expiry-invalid")
    return errors


REASON_DECISIONS = {
    "mandatory": {"include"},
    "step-required": {"include"},
    "budget-selected": {"include"},
    "budget-omitted": {"omit"},
    "jit-deferred": {"defer"},
    "legacy-full-fallback": {"include"},
}


def validate_context_plan(plan: dict, bundle: dict) -> list[str]:
    errors: list[str] = []
    if (plan.get("decision_id"), plan.get("bundle_id"), plan.get("bundle_sha256")) != (bundle.get("decision_id"), bundle.get("bundle_id"), bundle.get("bundle_sha256")):
        errors.append("context-plan-bundle-mismatch")
    sections = plan.get("sections", [])
    ids = [s.get("section_id") for s in sections]
    orders = [s.get("order") for s in sections]
    if len(ids) != len(set(ids)):
        errors.append("context-section-id-duplicate")
    if len(orders) != len(set(orders)) or sorted(orders) != list(range(len(orders))):
        errors.append("context-section-order-invalid")
    for section in sections:
        if section.get("decision") not in REASON_DECISIONS.get(section.get("reason_code"), set()):
            errors.append(f"context-reason-decision-invalid:{section.get('section_id')}")
        if section.get("class") == "mandatory-core" and section.get("decision") != "include":
            errors.append(f"context-mandatory-omitted:{section.get('section_id')}")
    budget = plan.get("budget", {})
    planned = sum(s.get("estimated_tokens", 0) for s in sections if s.get("decision") == "include")
    reserved = sum(s.get("estimated_tokens", 0) for s in sections if s.get("class") == "mandatory-core")
    if planned != budget.get("planned_tokens"):
        errors.append("context-planned-token-arithmetic")
    if reserved != budget.get("reserved_mandatory_tokens"):
        errors.append("context-mandatory-token-arithmetic")
    if planned > budget.get("limit_tokens", -1):
        errors.append("context-budget-exceeded")

    pins = {p.get("id"): canonical_sha256(p) for p in bundle.get("variable_pins", [])}
    variables = plan.get("variables", [])
    var_ids = [v.get("var_id") for v in variables]
    if len(var_ids) != len(set(var_ids)) or set(var_ids) != set(pins):
        errors.append("context-variable-cardinality-mismatch")
    for variable in variables:
        if pins.get(variable.get("var_id")) != variable.get("pin_sha256"):
            errors.append(f"context-variable-pin-mismatch:{variable.get('var_id')}")
    return errors


def credential_errors(document: dict) -> list[str]:
    """Scan user/task/state/change/session-bearing fields before persistence."""
    roots = []
    for key in ("task_description", "state_after", "changes"):
        if key in document:
            roots.append((key, document[key]))
    context = document.get("orchestrator_context", {})
    for key, value in context.items():
        if "session" in key.lower() or key in {"triggered_by", "cached_vars"}:
            roots.append((f"orchestrator_context.{key}", value))

    errors: list[str] = []

    def walk(path: str, value: object) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}"
                if SECRET_KEY.search(key):
                    errors.append(f"credential-key:{child_path}")
                walk(child_path, child)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(f"{path}[{index}]", child)
        elif isinstance(value, str) and SECRET_VALUE.search(value):
            errors.append(f"credential-value:{path}")

    for path, value in roots:
        walk(path, value)
    return errors
