#!/usr/bin/env python3
import copy
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]


def load(name):
    return json.loads((ROOT / "tests/fixtures/contracts/valid" / name).read_text())


def bundle_errors(bundle, attestation):
    errors = []
    if bundle["protocol_id"] != bundle["protocol_pin"]["id"]:
        errors.append("protocol-pin-mismatch")
    ids = [pin["id"] for pin in bundle["variable_pins"]]
    if ids != sorted(ids) or len(ids) != len(set(ids)):
        errors.append("variable-pins-not-unique-sorted")
    for pin in bundle["variable_pins"]:
        expected = (pin["id"], pin["version"], pin["content_sha256"], pin["validator_sha256"], pin["attestation_id"])
        actual = (attestation["var_id"], attestation["var_version"], attestation["var_sha256"], attestation["validator_sha256"], attestation["attestation_id"])
        if expected != actual:
            errors.append("attestation-pin-mismatch")
    return errors


bundle = load("context-bundle-v1.json")
attestation = load("validation-attestation.json")
# The fixture deliberately uses different placeholder hashes until aligned here.
bundle["variable_pins"][0]["content_sha256"] = attestation["var_sha256"]
bundle["variable_pins"][0]["validator_sha256"] = attestation["validator_sha256"]
assert bundle_errors(bundle, attestation) == []

tampered = copy.deepcopy(bundle)
tampered["protocol_pin"]["id"] = "other-protocol"
assert "protocol-pin-mismatch" in bundle_errors(tampered, attestation)

tampered = copy.deepcopy(bundle)
tampered["variable_pins"].append(copy.deepcopy(tampered["variable_pins"][0]))
assert "variable-pins-not-unique-sorted" in bundle_errors(tampered, attestation)

tampered = copy.deepcopy(bundle)
tampered["variable_pins"][0]["validator_sha256"] = "f" * 64
assert "attestation-pin-mismatch" in bundle_errors(tampered, attestation)

receipt = load("execution-receipt-v1.json")
assert receipt["run_id"] == bundle["run_id"]
assert receipt["plan_id"] == bundle["plan_id"]
assert receipt["bundle_id"] == bundle["bundle_id"]
assert receipt["bundle_sha256"] == bundle["bundle_sha256"]

plan = load("context-plan.json")
assert plan["bundle_id"] == bundle["bundle_id"]
assert plan["bundle_sha256"] == bundle["bundle_sha256"]
mandatory = [s for s in plan["sections"] if s["class"] == "mandatory-core"]
assert mandatory and all(s["decision"] == "include" and s["reason_code"] == "mandatory" for s in mandatory)

print("cross-contract invariants passed")
