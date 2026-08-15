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
    for item in decisions + plans + events:
        walk_privacy(item)
    bad_fallback = dict(decisions[3], match_disposition="specific_match")
    reject("route-decision.schema.json", bad_fallback)
    bad_ambiguous = dict(decisions[2], requires_operator_resolution=False)
    reject("route-decision.schema.json", bad_ambiguous)
    bad_event = dict(events[0], payload={"prompt": "forbidden"})
    reject("atp-event.schema.json", bad_event)
    bad_single = dict(plans[0], completion_policy={"mode": "all-steps-terminal", "aggregate_receipt_required": True})
    reject("execution-plan.schema.json", bad_single)
    print(f"validated {len(decisions)} decisions, {len(plans)} plans, {len(events)} events")


if __name__ == "__main__":
    main()
