"""Pure lifecycle state machine backed only by explicit in-memory adapters."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import PurePosixPath
import random
from typing import Any

from lib.contracts.validator import canonical_sha256, validate_bundle_receipt


PHASES = ("routing", "validation", "execution", "checkpoint", "receipt", "outcome")


class ScenarioError(RuntimeError):
    pass


class InjectedFault(ScenarioError):
    pass


@dataclass
class FakeFileSystem:
    files: dict[str, Any] = field(default_factory=lambda: {"/sandbox/state.json": {"count": 0}})
    writes: list[str] = field(default_factory=list)

    def write(self, target: str, value: Any) -> None:
        path = PurePosixPath(target)
        if not path.is_absolute() or path.parts[:2] != ("/", "sandbox"):
            raise ScenarioError("mutation-sentinel: path outside /sandbox")
        self.files[str(path)] = deepcopy(value)
        self.writes.append(str(path))

    def snapshot(self) -> bytes:
        return json.dumps(self.files, sort_keys=True, separators=(",", ":")).encode()

    def restore(self, snapshot: bytes) -> None:
        self.files = json.loads(snapshot)


@dataclass
class FakeCommandAdapter:
    calls: list[str] = field(default_factory=list)

    def run(self, operation: str) -> dict[str, Any]:
        self.calls.append(operation)
        return {"exit_code": 0, "stdout": "sanitized"}


@dataclass
class FakeEndpointAdapter:
    calls: list[str] = field(default_factory=list)

    def request(self, target: str) -> dict[str, Any]:
        if target.startswith(("http://", "https://")):
            raise ScenarioError("mutation-sentinel: network endpoint forbidden")
        self.calls.append(target)
        return {"status": 200, "body": "sanitized"}


@dataclass
class ProductionReadonlyAdapter:
    reads: list[str] = field(default_factory=list)

    def read(self, target: str) -> str:
        if not target.startswith("fixture://"):
            raise ScenarioError("mutation-sentinel: production adapter accepts fixture:// only")
        self.reads.append(target)
        return "sanitized-readonly-value"


@dataclass(frozen=True)
class LifecycleResult:
    status: str
    phases: tuple[str, ...]
    events: tuple[dict[str, Any], ...]
    mutated: bool
    rolled_back: bool
    receipt: dict[str, Any] | None
    state_sha256: str
    error: str | None


class Simulator:
    """Run a scenario deterministically; no adapter can perform real I/O."""

    def __init__(self, initial_files: dict[str, Any] | None = None):
        self.fs = FakeFileSystem(deepcopy(initial_files) if initial_files is not None else {"/sandbox/state.json": {"count": 0}})
        self.command = FakeCommandAdapter()
        self.endpoint = FakeEndpointAdapter()
        self.production_readonly = ProductionReadonlyAdapter()

    def run(self, scenario: dict[str, Any]) -> LifecycleResult:
        rng = random.Random(scenario["seed"])
        before = self.fs.snapshot()
        phases: list[str] = []
        events: list[dict[str, Any]] = []
        receipt: dict[str, Any] | None = None
        rolled_back = False
        error: str | None = None
        status = "failed"

        def enter(phase: str) -> None:
            phases.append(phase)
            events.append({"sequence": len(events), "phase": phase, "occurred_at": scenario["clock"]})
            fault = scenario.get("fault")
            if fault and fault["phase"] == phase:
                raise InjectedFault(f"{phase}:{fault.get('kind', 'injected')}")

        try:
            enter("routing")
            protocol = scenario["protocol"]
            if not protocol["id"]:
                raise ScenarioError("no-route")

            enter("validation")
            available, valid = set(scenario["variables"]["available"]), set(scenario["variables"]["valid"])
            required = set(protocol["required_vars"])
            if missing := required - available:
                raise ScenarioError("required-var-missing:" + ",".join(sorted(missing)))
            if invalid := required - valid:
                raise ScenarioError("required-var-invalid:" + ",".join(sorted(invalid)))
            undeclared = {step["tool"] for step in scenario["steps"]} - set(protocol["tool_allowlist"])
            if undeclared:
                raise ScenarioError("tool-not-allowed:" + ",".join(sorted(undeclared)))

            enter("execution")
            for step in scenario["steps"]:
                tool = step["tool"]
                if tool == "filesystem":
                    self.fs.write(step.get("target", ""), step.get("value"))
                elif tool == "command":
                    self.command.run(step["operation"])
                elif tool == "endpoint":
                    self.endpoint.request(step.get("target", ""))
                elif tool == "production-readonly":
                    self.production_readonly.read(step.get("target", ""))
                else:
                    raise ScenarioError("unknown-tool:" + tool)

            enter("checkpoint")
            enter("receipt")
            variant = scenario.get("receipt_variant", "valid")
            if variant == "missing":
                raise ScenarioError("receipt-missing")
            bundle, receipt = self._receipt(scenario, rng)
            if variant == "forged":
                receipt["receipt_sha256"] = "0" * 64
            elif variant == "invalid":
                receipt.pop("protocol_id")
            if not self._receipt_valid(bundle, receipt):
                raise ScenarioError("receipt-invalid")

            enter("outcome")
            status = "completed"
        except (ScenarioError, InjectedFault) as exc:
            error = str(exc)
            mutated = self.fs.snapshot() != before
            mode = scenario["protocol"]["checkpoint_mode"]
            if mutated and mode == "rollback-and-stop":
                self.fs.restore(before)
                rolled_back = True
                status = "failed"
            elif mutated:
                status = "partial"
            else:
                status = "violated" if error.startswith(("receipt-", "tool-not-allowed")) else "failed"

        after = self.fs.snapshot()
        return LifecycleResult(
            status=status,
            phases=tuple(phases),
            events=tuple(events),
            mutated=after != before,
            rolled_back=rolled_back,
            receipt=receipt,
            state_sha256=hashlib.sha256(after).hexdigest(),
            error=error,
        )

    @staticmethod
    def _receipt(scenario: dict[str, Any], rng: random.Random) -> tuple[dict[str, Any], dict[str, Any]]:
        ids = {
            "decision_id": f"dec_{rng.getrandbits(128):032x}",
            "run_id": f"run_{rng.getrandbits(128):032x}",
            "plan_id": f"pln_{rng.getrandbits(128):032x}",
            "bundle_id": f"bnd_{rng.getrandbits(128):032x}",
        }
        protocol_pin = {
            "kind": "protocol",
            "id": scenario["protocol"]["id"],
            "version": "1.0.0",
            "schema_version": "1.0.0",
            "content_sha256": canonical_sha256(scenario["protocol"]),
        }
        bundle = {
            **ids,
            "protocol_id": scenario["protocol"]["id"],
            "protocol_pin": protocol_pin,
            "variable_pins": [],
        }
        bundle["bundle_sha256"] = canonical_sha256(bundle)
        receipt = {
            "receipt_id": f"rcp_{rng.getrandbits(128):032x}",
            "schema_version": "1.0.0",
            **ids,
            "protocol_id": scenario["protocol"]["id"],
            "bundle_sha256": bundle["bundle_sha256"],
            "protocol_pin": protocol_pin,
            "variable_pins": [],
            "completed_at": scenario["clock"],
            "execution_phase_reached": "output",
            "result": "success",
            "changes": [],
            "var_updates": [],
            "next_action": "none",
            "state_after": {"summary": "sanitized simulator state"},
            "evidence": [],
            "rollback": "Restore the in-memory checkpoint.",
            "remaining_risks": [],
            "next_package": None,
        }
        receipt["receipt_sha256"] = canonical_sha256(receipt)
        return bundle, receipt

    @staticmethod
    def _receipt_valid(bundle: dict[str, Any], receipt: dict[str, Any]) -> bool:
        required = {
            "receipt_id", "schema_version", "decision_id", "run_id", "plan_id",
            "bundle_id", "protocol_id", "bundle_sha256", "protocol_pin",
            "variable_pins", "completed_at", "result", "receipt_sha256",
        }
        if not required <= receipt.keys():
            return False
        return not validate_bundle_receipt(bundle, receipt, [])
