#!/usr/bin/env python3
from copy import deepcopy
from datetime import datetime, timezone
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from lib.contracts.validator import (  # noqa: E402
    canonical_sha256,
    credential_errors,
    validate_bundle_receipt,
    validate_context_plan,
    validate_ledger,
)


def load(name):
    return json.loads((ROOT / "tests/fixtures/contracts/valid" / name).read_text())


def require(error, errors):
    assert error in errors, (error, errors)


def seal_event(event):
    event["event_sha256"] = canonical_sha256({k: v for k, v in event.items() if k != "event_sha256"})
    return event


bundle = load("context-bundle-v1.json")
attestation = load("validation-attestation.json")
receipt = load("execution-receipt-v1.json")
plan = load("context-plan.json")
plan["variables"][0]["pin_sha256"] = canonical_sha256(bundle["variable_pins"][0])

# Exact receipt/bundle pins and one attestation per variable pin.
assert validate_bundle_receipt(bundle, receipt, [attestation]) == []
bad_bundle = deepcopy(bundle); bad_bundle["bundle_sha256"] = "f" * 64
require("bundle-hash-mismatch", validate_bundle_receipt(bad_bundle, receipt, [attestation]))
bad = deepcopy(receipt); bad["receipt_sha256"] = "f" * 64
require("receipt-hash-mismatch", validate_bundle_receipt(bundle, bad, [attestation]))
bad = deepcopy(receipt); bad["protocol_pin"]["content_sha256"] = "f" * 64
require("protocol-pin-mismatch", validate_bundle_receipt(bundle, bad, [attestation]))
bad = deepcopy(receipt); bad["variable_pins"] = []
require("variable-pins-mismatch", validate_bundle_receipt(bundle, bad, [attestation]))
require("attestation-cardinality-mismatch", validate_bundle_receipt(bundle, receipt, []))
bad_att = deepcopy(attestation); bad_att["validator_sha256"] = "f" * 64
require("attestation-pin-mismatch:example-state", validate_bundle_receipt(bundle, receipt, [bad_att]))

# Exactly one pending event, contiguous sequence/hash links, tamper detection,
# receipt-backed completion, and unexpired operator bypass.
pending = load("ledger-pending.json")
submitted = seal_event({
    **pending, "event_id": "le_66666666666666666666666666666666", "sequence": 1,
    "event_type": "receipt-submitted", "previous_event_sha256": pending["event_sha256"],
    "occurred_at": "2026-08-15T20:02:00Z",
    "receipt_id": receipt["receipt_id"], "receipt_sha256": receipt["receipt_sha256"],
})
completed = seal_event({
    **submitted, "event_id": "le_77777777777777777777777777777777", "sequence": 2,
    "event_type": "completed", "previous_event_sha256": submitted["event_sha256"],
    "occurred_at": "2026-08-15T20:03:00Z",
})
clock = datetime(2026, 8, 15, 20, 4, tzinfo=timezone.utc)
assert validate_ledger([pending, submitted, completed], clock) == []
require("ledger-pending-cardinality", validate_ledger([submitted], clock))
bad = deepcopy(completed); bad["sequence"] = 3
require("ledger-sequence-not-contiguous", validate_ledger([pending, submitted, bad], clock))
bad = deepcopy(completed); bad["previous_event_sha256"] = "f" * 64
require("ledger-previous-hash-mismatch:2", validate_ledger([pending, submitted, bad], clock))
bad = deepcopy(submitted); bad["event_sha256"] = "f" * 64
require("ledger-event-hash-mismatch:1", validate_ledger([pending, bad], clock))
bad = deepcopy(submitted); bad["run_id"] = "run_ffffffffffffffffffffffffffffffff"
require("ledger-correlation-mismatch", validate_ledger([pending, bad], clock))
tamper = deepcopy(submitted); tamper["event_sha256"] = "f" * 64
require("ledger-duplicate-id-tamper", validate_ledger([pending, submitted, tamper], clock))
require("ledger-duplicate-event", validate_ledger([pending, submitted, deepcopy(submitted)], clock))
require("ledger-completed-without-submitted-receipt", validate_ledger([pending, completed], clock))
after = deepcopy(completed); after["event_id"] = "le_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"; after["sequence"] = 3; after["event_type"] = "reconciled"; after["previous_event_sha256"] = completed["event_sha256"]
require("ledger-event-after-terminal", validate_ledger([pending, submitted, completed, after], clock))
bypass = {
    **submitted, "event_id": "le_88888888888888888888888888888888", "event_type": "bypass-granted",
    "reason": "sanitized emergency authorization", "bypass_expires_at": "2026-08-15T20:03:00Z",
    "actor": {"kind": "operator", "id_sha256": "a" * 64},
}
require("ledger-bypass-expired", validate_ledger([pending, bypass], clock))
valid_bypass = deepcopy(bypass); valid_bypass["bypass_expires_at"] = "2026-08-15T20:10:00Z"; seal_event(valid_bypass)
assert validate_ledger([pending, valid_bypass], clock) == []

# Budget arithmetic, mandatory preservation, stable IDs/orders, reason/decision
# combinations, and exact bundle variable coverage.
assert validate_context_plan(plan, bundle) == []
bad = deepcopy(plan); bad["budget"]["planned_tokens"] += 1
require("context-planned-token-arithmetic", validate_context_plan(bad, bundle))
bad = deepcopy(plan); bad["budget"]["limit_tokens"] = 1000
require("context-budget-exceeded", validate_context_plan(bad, bundle))
bad = deepcopy(plan); bad["sections"][0]["decision"] = "omit"
require("context-mandatory-omitted:core", validate_context_plan(bad, bundle))
bad = deepcopy(plan); bad["sections"][1]["section_id"] = "core"
require("context-section-id-duplicate", validate_context_plan(bad, bundle))
bad = deepcopy(plan); bad["sections"][1]["order"] = 0
require("context-section-order-invalid", validate_context_plan(bad, bundle))
bad = deepcopy(plan); bad["sections"][1]["reason_code"] = "budget-omitted"
require("context-reason-decision-invalid:reference.example", validate_context_plan(bad, bundle))
bad = deepcopy(plan); bad["variables"] = []
require("context-variable-cardinality-mismatch", validate_context_plan(bad, bundle))
bad = deepcopy(plan); bad["variables"][0]["pin_sha256"] = "f" * 64
require("context-variable-pin-mismatch:example-state", validate_context_plan(bad, bundle))

# Credential sanitizer covers task, post-state, change, and session-bearing data.
assert credential_errors({"task_description": "Inspect sanitized example state."}) == []
assert credential_errors({"state_after": {"token_count": 42}}) == []
assert credential_errors({"task_description": "use Bearer abcdefghijklmnop"})
assert credential_errors({"state_after": {"api_key": "redacted"}})
assert credential_errors({"changes": [{"summary": "-----BEGIN PRIVATE KEY-----"}]})
assert credential_errors({"orchestrator_context": {"session_id": "discord:raw-session-value"}})

print("cross-contract invariants and adversarial negatives passed")
