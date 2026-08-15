#!/usr/bin/env python3
import json
from pathlib import Path

from jsonschema import Draft7Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "schema"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
FORBIDDEN_KEYS = {"prompt", "secret", "token", "password", "session_key", "session-key", "private_var_value", "raw_content", "absolute_path"}


def load(name):
    return json.loads((SCHEMA / name).read_text())


def validate(schema_name, values):
    validator = Draft7Validator(load(schema_name), format_checker=FormatChecker())
    for index, value in enumerate(values):
        errors = sorted(validator.iter_errors(value), key=lambda error: list(error.path))
        assert not errors, f"{schema_name} fixture {index}: " + "; ".join(error.message for error in errors)


def reject(schema_name, value):
    errors = list(Draft7Validator(load(schema_name), format_checker=FormatChecker()).iter_errors(value))
    assert errors, f"{schema_name} unexpectedly accepted invalid fixture"


def walk_privacy(value):
    if isinstance(value, dict):
        for key, child in value.items():
            assert key.lower() not in FORBIDDEN_KEYS, f"forbidden fixture key: {key}"
            walk_privacy(child)
    elif isinstance(value, list):
        for child in value:
            walk_privacy(child)
    elif isinstance(value, str):
        assert not value.startswith("/home/"), "absolute private path in fixture"


def validate_plan_graph(plan):
    ids = [step["step_id"] for step in plan["steps"]]
    bundles = [step["bundle_id"] for step in plan["steps"]]
    assert len(ids) == len(set(ids)), "duplicate step_id"
    assert len(bundles) == len(set(bundles)), "duplicate bundle_id"
    dependencies = {step["step_id"]: step["depends_on"] for step in plan["steps"]}
    for step_id, deps in dependencies.items():
        assert step_id not in deps, "self dependency"
        assert set(deps) <= set(ids), "unknown dependency"
    visiting, visited = set(), set()
    def visit(node):
        assert node not in visiting, "cycle detected"
        if node in visited:
            return
        visiting.add(node)
        for dep in dependencies[node]:
            visit(dep)
        visiting.remove(node)
        visited.add(node)
    for step_id in ids:
        visit(step_id)


def has_dependency_path(dependencies, source, target):
    pending, seen = list(dependencies[source]), set()
    while pending:
        node = pending.pop()
        if node == target:
            return True
        if node not in seen:
            seen.add(node)
            pending.extend(dependencies[node])
    return False


def scopes_overlap(left, right):
    return left == right or left.startswith(right.rstrip("/") + "/") or right.startswith(left.rstrip("/") + "/")


def validate_cross_contract(decisions, plans):
    decision_by_id = {item["decision_id"]: item for item in decisions}
    assert len(decision_by_id) == len(decisions), "duplicate decision_id"
    for decision in decisions:
        candidates = {item["protocol_id"]: item for item in decision["candidates"]}
        for protocol_id in decision.get("selected_protocol_ids", []):
            assert protocol_id in candidates, "selected protocol missing from candidates"
            candidate = candidates[protocol_id]
            assert candidate["authorization_basis"] in {"explicit", "deterministic-rule"}, "selected protocol lacks authorization"
            assert set(candidate["evidence"]) != {"semantic-retrieval"}, "semantic evidence cannot solely authorize selection"
    for plan in plans:
        decision = decision_by_id[plan["decision_id"]]
        assert plan["request_id"] == decision["request_id"], "plan request does not match decision"
        assert plan["plan_id"] == decision["plan_id"], "plan id does not match decision"
        assert {step["protocol_id"] for step in plan["steps"]} <= set(decision["selected_protocol_ids"]), "plan step was not selected"
        dependencies = {step["step_id"]: step["depends_on"] for step in plan["steps"]}
        groups = [set(group["step_ids"]) for group in plan.get("serialization_groups", [])]
        for index, left in enumerate(plan["steps"]):
            for right in plan["steps"][index + 1:]:
                if any(scopes_overlap(a, b) for a in left["mutation_scope"] for b in right["mutation_scope"]):
                    ordered = has_dependency_path(dependencies, left["step_id"], right["step_id"]) or has_dependency_path(dependencies, right["step_id"], left["step_id"])
                    serialized = any({left["step_id"], right["step_id"]} <= group for group in groups)
                    assert ordered or serialized, "overlapping mutation scopes are unordered"


def main():
    decisions = json.loads((FIXTURES / "route-decisions.json").read_text())
    plans = json.loads((FIXTURES / "execution-plans.json").read_text())
    events = [json.loads(line) for line in (FIXTURES / "events.jsonl").read_text().splitlines() if line]
    validate("route-decision.schema.json", decisions)
    validate("execution-plan.schema.json", plans)
    validate("atp-event.schema.json", events)
    assert {item["disposition"] for item in decisions} == {"single", "composite", "ambiguous", "fallback", "none"}
    assert {item["match_disposition"] for item in decisions} == {"specific_match", "composite_match", "ambiguous", "wildcard_fallback", "no_route", "routing_error"}
    for plan in plans:
        validate_plan_graph(plan)
    validate_cross_contract(decisions, plans)
    for item in decisions + plans + events:
        walk_privacy(item)
    bad_fallback = dict(decisions[3], match_disposition="specific_match")
    reject("route-decision.schema.json", bad_fallback)
    bad_ambiguous = dict(decisions[2], requires_operator_resolution=False)
    reject("route-decision.schema.json", bad_ambiguous)
    bad_event = dict(events[0], payload={"prompt": "forbidden"})
    reject("atp-event.schema.json", bad_event)
    for payload in (
        {"outer": {"session_key": "forbidden"}},
        {"outer": [{"secret_value": "forbidden"}]},
        {"outer": {"location": "/home/example/private.json"}},
    ):
        reject("atp-event.schema.json", dict(events[0], payload=payload))
    missing_decision_correlation = json.loads(json.dumps(events[1]))
    del missing_decision_correlation["correlation"]["decision_id"]
    reject("atp-event.schema.json", missing_decision_correlation)
    bad_single = dict(plans[0], completion_policy={"mode": "all-steps-terminal", "aggregate_receipt_required": True})
    reject("execution-plan.schema.json", bad_single)
    unauthorized = json.loads(json.dumps(decisions))
    unauthorized[0]["selected_protocol_ids"] = ["missing-protocol"]
    try:
        validate_cross_contract(unauthorized, plans)
        raise AssertionError("unauthorized selected route was accepted")
    except AssertionError as error:
        assert str(error) == "selected protocol missing from candidates"
    semantic_only = json.loads(json.dumps(decisions))
    semantic_only[0]["candidates"][0]["evidence"] = ["semantic-retrieval"]
    semantic_only[0]["candidates"][0]["authorization_basis"] = "semantic-support-only"
    try:
        validate_cross_contract(semantic_only, plans)
        raise AssertionError("semantic-only selected route was accepted")
    except AssertionError as error:
        assert str(error) == "selected protocol lacks authorization"
    wrong_step = json.loads(json.dumps(plans))
    wrong_step[0]["steps"][0]["protocol_id"] = "unselected-protocol"
    try:
        validate_cross_contract(decisions, wrong_step)
        raise AssertionError("unselected plan step was accepted")
    except AssertionError as error:
        assert str(error) == "plan step was not selected"
    unordered = json.loads(json.dumps(plans))
    unordered[1]["steps"][1]["depends_on"] = []
    unordered[1]["serialization_groups"] = []
    try:
        validate_cross_contract(decisions, unordered)
        raise AssertionError("unordered mutation overlap was accepted")
    except AssertionError as error:
        assert str(error) == "overlapping mutation scopes are unordered"
    print(f"validated {len(decisions)} decisions, {len(plans)} plans, {len(events)} events")


if __name__ == "__main__":
    main()
