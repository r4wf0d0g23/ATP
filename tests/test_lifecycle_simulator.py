import json
from pathlib import Path
import unittest

from jsonschema import Draft7Validator, FormatChecker

from lib.lifecycle_simulator import Simulator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "lib/lifecycle-simulator/schema/scenario.schema.json").read_text())
RECEIPT_SCHEMA = json.loads((ROOT / "lib/execution-receipt/schema/handoff-artifact.schema.json").read_text())
HAPPY = json.loads((ROOT / "tests/fixtures/lifecycle/happy.json").read_text())
ROUTE_COVERAGE = json.loads((ROOT / "tests/fixtures/lifecycle/active-route-coverage.json").read_text())


class LifecycleSimulatorTests(unittest.TestCase):
    def scenario(self, **updates):
        value = json.loads(json.dumps(HAPPY))
        value.update(updates)
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

    def test_required_var_failure_halts_before_mutation(self):
        scenario = self.scenario(variables={"available": [], "valid": []})
        result = Simulator().run(scenario)
        self.assertEqual(result.phases, ("routing", "validation"))
        self.assertFalse(result.mutated)
        self.assertIn("required-var-missing", result.error)

    def test_tool_allowlist_halts_before_mutation(self):
        protocol = dict(HAPPY["protocol"], tool_allowlist=["command"])
        result = Simulator().run(self.scenario(protocol=protocol))
        self.assertEqual(result.status, "violated")
        self.assertFalse(result.mutated)

    def test_fault_injection_at_every_phase(self):
        for phase in ("routing", "validation", "execution", "checkpoint", "receipt", "outcome"):
            with self.subTest(phase=phase):
                result = Simulator().run(self.scenario(fault={"phase": phase, "kind": "test"}))
                self.assertNotEqual(result.status, "completed")
                self.assertIn(phase, result.phases)

    def test_sanitized_active_route_inventory_has_happy_and_failure_paths(self):
        self.assertEqual(len(ROUTE_COVERAGE["routes"]), 10)
        self.assertEqual(len(set(ROUTE_COVERAGE["routes"])), 10)
        for route in ROUTE_COVERAGE["routes"]:
            protocol = dict(HAPPY["protocol"], id=route)
            happy = Simulator().run(self.scenario(protocol=protocol))
            failed = Simulator().run(self.scenario(protocol=protocol, variables={"available": [], "valid": []}))
            self.assertEqual(happy.status, "completed")
            self.assertEqual(failed.status, "failed")
            self.assertFalse(failed.mutated)

    def test_all_checkpoint_modes(self):
        for mode, status, mutated, rolled_back in (
            ("write-handoff-artifact", "partial", True, False),
            ("commit-and-stop", "partial", True, False),
            ("rollback-and-stop", "failed", False, True),
        ):
            with self.subTest(mode=mode):
                protocol = dict(HAPPY["protocol"], checkpoint_mode=mode)
                result = Simulator().run(self.scenario(protocol=protocol, fault={"phase": "checkpoint"}))
                self.assertEqual((result.status, result.mutated, result.rolled_back), (status, mutated, rolled_back))

    def test_rollback_is_byte_identical(self):
        simulator = Simulator()
        before = simulator.fs.snapshot()
        result = simulator.run(self.scenario(fault={"phase": "receipt"}))
        self.assertTrue(result.rolled_back)
        self.assertEqual(simulator.fs.snapshot(), before)

    def test_missing_forged_and_invalid_receipts_never_complete(self):
        for variant in ("missing", "forged", "invalid"):
            with self.subTest(variant=variant):
                result = Simulator().run(self.scenario(receipt_variant=variant))
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
                result = Simulator().run(self.scenario(steps=steps))
                self.assertNotEqual(result.status, "completed")
                self.assertIn("mutation-sentinel", result.error)


if __name__ == "__main__":
    unittest.main()
