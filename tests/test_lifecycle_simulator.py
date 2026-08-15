import json
from pathlib import Path
import unittest

from jsonschema import Draft7Validator, FormatChecker

from lib.lifecycle_simulator import Simulator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "lib/lifecycle-simulator/schema/scenario.schema.json").read_text())
RECEIPT_SCHEMA = json.loads((ROOT / "lib/execution-receipt/schema/handoff-artifact.schema.json").read_text())
EVENT_SCHEMA = json.loads((ROOT / "schema/atp-event.schema.json").read_text())
HAPPY = json.loads((ROOT / "tests/fixtures/lifecycle/happy.json").read_text())
ROUTE_COVERAGE = json.loads((ROOT / "tests/fixtures/lifecycle/active-route-coverage.json").read_text())


class LifecycleSimulatorTests(unittest.TestCase):
    def scenario(self, *, expected_status=None, expected_mutated=None, expected_state=None, **updates):
        value = json.loads(json.dumps(HAPPY))
        value.update(updates)
        if expected_status is not None:
            value["expected"] = {
                "status": expected_status,
                "mutated": expected_mutated,
                "final_state": expected_state,
            }
        return value

    def test_public_scenario_fixture_validates(self):
        Draft7Validator(SCHEMA, format_checker=FormatChecker()).validate(HAPPY)

    def test_happy_path_is_deterministic_and_covers_entire_lifecycle(self):
        first = Simulator().run(HAPPY)
        second = Simulator().run(HAPPY)
        self.assertEqual(first, second)
        self.assertEqual(first.status, "completed")
        self.assertEqual(first.phases, ("routing", "validation", "execution", "checkpoint", "receipt", "outcome"))
        self.assertTrue(first.mutated)
        Draft7Validator(RECEIPT_SCHEMA, format_checker=FormatChecker()).validate(first.receipt)
        for event in first.events:
            Draft7Validator(EVENT_SCHEMA, format_checker=FormatChecker()).validate(event)
        self.assertEqual(tuple(item["phase"] for item in first.trace), first.phases)

    def test_required_var_failure_halts_before_mutation(self):
        scenario = self.scenario(variables={"available": [], "valid": []}, expected_status="failed", expected_mutated=False, expected_state={"/sandbox/state.json": {"count": 0}})
        result = Simulator().run(scenario)
        self.assertEqual(result.phases, ("routing", "validation"))
        self.assertFalse(result.mutated)
        self.assertIn("required-var-missing", result.error)

    def test_tool_allowlist_halts_before_mutation(self):
        protocol = dict(HAPPY["protocol"], tool_allowlist=["command"])
        result = Simulator().run(self.scenario(protocol=protocol, expected_status="violated", expected_mutated=False, expected_state={"/sandbox/state.json": {"count": 0}}))
        self.assertEqual(result.status, "violated")
        self.assertFalse(result.mutated)

    def test_fault_injection_at_every_phase(self):
        for phase in ("routing", "validation", "execution", "checkpoint", "receipt", "outcome"):
            with self.subTest(phase=phase):
                result = Simulator().run(self.scenario(fault={"phase": phase, "kind": "test"}, expected_status="failed", expected_mutated=False, expected_state={"/sandbox/state.json": {"count": 0}}))
                self.assertNotEqual(result.status, "completed")
                self.assertIn(phase, result.phases)

    def test_sanitized_active_route_inventory_has_happy_and_failure_paths(self):
        self.assertEqual(len(ROUTE_COVERAGE["routes"]), 10)
        self.assertEqual(len({route["id"] for route in ROUTE_COVERAGE["routes"]}), 10)
        behavioral_signatures = set()
        for route in ROUTE_COVERAGE["routes"]:
            behavioral_signatures.add((tuple(route["required_vars"]), tuple(route["tools"]), route["checkpoint_mode"], tuple(step["operation"] for step in route["steps"])))
            protocol = {
                "id": route["id"], "required_vars": route["required_vars"],
                "tool_allowlist": route["tools"], "checkpoint_mode": route["checkpoint_mode"],
                "clean_state_definition": f"The sanitized {route['id']} state has a durable checkpoint.",
            }
            variables = {"available": route["required_vars"], "valid": route["required_vars"]}
            expected_state = {"/sandbox/state.json": {"count": 0}}
            for step in route["steps"]:
                if step["tool"] == "filesystem":
                    expected_state[step["target"]] = step["value"]
            happy = Simulator().run(self.scenario(protocol=protocol, variables=variables, steps=route["steps"], expected_status="completed", expected_mutated=expected_state != {"/sandbox/state.json": {"count": 0}}, expected_state=expected_state))
            failed = Simulator().run(self.scenario(protocol=protocol, variables={"available": [], "valid": []}, steps=route["steps"], expected_status="failed", expected_mutated=False, expected_state={"/sandbox/state.json": {"count": 0}}))
            self.assertEqual(happy.status, "completed")
            self.assertEqual(failed.status, "failed")
            self.assertFalse(failed.mutated)
        self.assertEqual(len(behavioral_signatures), 10)

    def test_all_checkpoint_modes(self):
        for mode, status, mutated, rolled_back in (
            ("write-handoff-artifact", "partial", True, False),
            ("commit-and-stop", "partial", True, False),
            ("rollback-and-stop", "failed", False, True),
        ):
            with self.subTest(mode=mode):
                protocol = dict(HAPPY["protocol"], checkpoint_mode=mode)
                final_state = {"/sandbox/state.json": {"count": 0 if rolled_back else 1}}
                result = Simulator().run(self.scenario(protocol=protocol, fault={"phase": "checkpoint"}, expected_status=status, expected_mutated=mutated, expected_state=final_state))
                self.assertEqual((result.status, result.mutated, result.rolled_back), (status, mutated, rolled_back))
                if status == "partial":
                    self.assertIsNotNone(result.safe_checkpoint)
                    self.assertEqual(result.safe_checkpoint["clean_state_definition"], protocol["clean_state_definition"])
                    self.assertEqual(result.safe_checkpoint["state_sha256"], result.state_sha256)

    def test_rollback_is_byte_identical(self):
        simulator = Simulator()
        before = simulator.fs.snapshot()
        result = simulator.run(self.scenario(fault={"phase": "receipt"}, expected_status="failed", expected_mutated=False, expected_state={"/sandbox/state.json": {"count": 0}}))
        self.assertTrue(result.rolled_back)
        self.assertEqual(simulator.fs.snapshot(), before)

    def test_missing_forged_and_invalid_receipts_never_complete(self):
        for variant in ("missing", "forged", "invalid"):
            with self.subTest(variant=variant):
                result = Simulator().run(self.scenario(receipt_variant=variant, expected_status="failed", expected_mutated=False, expected_state={"/sandbox/state.json": {"count": 0}}))
                self.assertNotEqual(result.status, "completed")
                self.assertNotIn("outcome", result.phases)

    def test_mutation_sentinel_blocks_paths_and_network(self):
        cases = [
            [{"tool": "filesystem", "operation": "write", "target": "/etc/config", "value": 1}],
            [{"tool": "endpoint", "operation": "get", "target": "https://example.invalid"}],
            [{"tool": "production-readonly", "operation": "read", "target": "/production/state"}],
        ]
        for steps in cases:
            with self.subTest(steps=steps):
                result = Simulator().run(self.scenario(steps=steps, expected_status="failed", expected_mutated=False, expected_state={"/sandbox/state.json": {"count": 0}}))
                self.assertNotEqual(result.status, "completed")
                self.assertIn("mutation-sentinel", result.error)

    def test_expected_outcome_mismatch_fails_the_scenario(self):
        scenario = self.scenario()
        scenario["expected"]["status"] = "failed"
        with self.assertRaisesRegex(AssertionError, "expectation mismatch"):
            Simulator().run(scenario)

    def test_traversal_normalization_and_symlink_escapes_are_rejected(self):
        probes = [
            ("/sandbox/../etc/config", {}),
            ("/sandbox/link/config", {"/sandbox/link": "/outside"}),
            ("/sandbox/a/file", {"/sandbox/a": "/sandbox/b", "/sandbox/b": "/outside"}),
            ("/sandbox/a/file", {"/sandbox/a": "/sandbox/b", "/sandbox/b": "/sandbox/a"}),
        ]
        for target, symlinks in probes:
            with self.subTest(target=target, symlinks=symlinks):
                steps = [{"tool": "filesystem", "operation": "write", "target": target, "value": "blocked"}]
                scenario = self.scenario(steps=steps, expected_status="failed", expected_mutated=False, expected_state={"/sandbox/state.json": {"count": 0}})
                result = Simulator(symlinks=symlinks).run(scenario)
                self.assertIn("mutation-sentinel", result.error)

    def test_receipt_failure_under_partial_mode_persists_safe_checkpoint(self):
        protocol = dict(HAPPY["protocol"], checkpoint_mode="write-handoff-artifact", clean_state_definition="The changed fixture is hashed and recoverable from the checkpoint artifact.")
        expected_state = {"/sandbox/state.json": {"count": 1}}
        result = Simulator().run(self.scenario(protocol=protocol, receipt_variant="forged", expected_status="partial", expected_mutated=True, expected_state=expected_state))
        self.assertEqual(result.status, "partial")
        self.assertEqual(result.safe_checkpoint["clean_state_definition"], protocol["clean_state_definition"])
        self.assertEqual(result.safe_checkpoint["state_sha256"], result.state_sha256)


if __name__ == "__main__":
    unittest.main()
