"""Pure lifecycle state machine backed only by explicit in-memory adapters."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
import json
import posixpath
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
    symlinks: dict[str, str] = field(default_factory=dict)
    writes: list[str] = field(default_factory=list)

    def resolve(self, target: str) -> str:
        if not target.startswith("/") or ".." in target.split("/"):
            raise ScenarioError("mutation-sentinel: non-canonical or traversing path")
        path = posixpath.normpath(target)
        seen: set[str] = set()
        while True:
            match = next((link for link in sorted(self.symlinks, key=len, reverse=True) if path == link or path.startswith(link + "/")), None)
            if match is None:
                break
            if match in seen:
                raise ScenarioError("mutation-sentinel: symlink cycle")
            seen.add(match)
            suffix = path[len(match):].lstrip("/")
            path = posixpath.normpath(posixpath.join(self.symlinks[match], suffix))
        if path != "/sandbox" and not path.startswith("/sandbox/"):
            raise ScenarioError("mutation-sentinel: resolved path outside /sandbox")
        return path

    def write(self, target: str, value: Any) -> None:
        path = self.resolve(target)
        self.files[path] = deepcopy(value)
        self.writes.append(path)

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
    trace: tuple[dict[str, Any], ...]
    mutated: bool
    rolled_back: bool
    safe_checkpoint: dict[str, Any] | None
    checkpoint_mode: str
    receipt: dict[str, Any] | None
    state_sha256: str
    error: str | None


class Simulator:
    """Run a scenario deterministically; no adapter can perform real I/O."""

    def __init__(self, initial_files: dict[str, Any] | None = None, symlinks: dict[str, str] | None = None):
        self.fs = FakeFileSystem(deepcopy(initial_files) if initial_files is not None else {"/sandbox/state.json": {"count": 0}}, deepcopy(symlinks or {}))
        self.command = FakeCommandAdapter()
        self.endpoint = FakeEndpointAdapter()
        self.production_readonly = ProductionReadonlyAdapter()

    def run(self, scenario: dict[str, Any]) -> LifecycleResult:
        rng = random.Random(scenario["seed"])
        before = self.fs.snapshot()
        ids = self._ids(rng)
        phases: list[str] = []
        trace: list[dict[str, Any]] = []
        events: list[dict[str, Any]] = []
        receipt: dict[str, Any] | None = None
        rolled_back = False
        safe_checkpoint: dict[str, Any] | None = None
        error: str | None = None
        status = "failed"

        def enter(phase: str) -> None:
            phases.append(phase)
            trace.append({"sequence": len(trace), "phase": phase, "occurred_at": scenario["clock"]})
            events.append(self._event(phase, len(events), scenario["clock"], ids, events[-1]["event_id"] if events else None))
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
            undeclared = {step["permission"] for step in scenario["steps"]} - set(protocol["tool_allowlist"])
            if undeclared:
                raise ScenarioError("permission-not-allowed:" + ",".join(sorted(undeclared)))

            if protocol["checkpoint_mode"] == "not-applicable":
                unsafe = set(protocol["tool_allowlist"]) - {"read"}
                if unsafe:
                    raise ScenarioError("not-applicable-requires-read-only-permissions")

            if scenario["steps"] or protocol["checkpoint_mode"] != "not-applicable":
                enter("execution")
            for step in scenario["steps"]:
                adapter = step["adapter"]
                if adapter == "fixture-filesystem":
                    self.fs.write(step.get("target", ""), step.get("value"))
                elif adapter == "fake-command":
                    self.command.run(step["operation"])
                elif adapter == "fake-endpoint":
                    self.endpoint.request(step.get("target", ""))
                elif adapter == "production-readonly":
                    self.production_readonly.read(step.get("target", ""))
                else:
                    raise ScenarioError("unknown-adapter:" + adapter)

            if protocol["checkpoint_mode"] == "not-applicable":
                enter("outcome")
                status = "completed"
                raise StopIteration

            enter("checkpoint")
            enter("receipt")
            variant = scenario.get("receipt_variant", "valid")
            if variant == "missing":
                raise ScenarioError("receipt-missing")
            bundle, receipt = self._receipt(scenario, rng, ids)
            if variant == "forged":
                receipt["receipt_sha256"] = "0" * 64
            elif variant == "invalid":
                receipt.pop("protocol_id")
            if not self._receipt_valid(bundle, receipt):
                raise ScenarioError("receipt-invalid")

            enter("outcome")
            status = "completed"
        except StopIteration:
            pass
        except ScenarioError as exc:
            error = str(exc)
            mutated = self.fs.snapshot() != before
            mode = scenario["protocol"]["checkpoint_mode"]
            if mutated and mode == "rollback-and-stop":
                self.fs.restore(before)
                rolled_back = True
                status = "failed"
            elif mutated:
                safe_checkpoint = {
                    "mode": mode,
                    "clean_state_definition": scenario["protocol"]["clean_state_definition"],
                    "state_sha256": hashlib.sha256(self.fs.snapshot()).hexdigest(),
                    "artifact_sha256": canonical_sha256({
                        "mode": mode,
                        "clean_state_definition": scenario["protocol"]["clean_state_definition"],
                        "state_sha256": hashlib.sha256(self.fs.snapshot()).hexdigest(),
                    }),
                }
                status = "partial"
            else:
                status = "violated" if error.startswith(("receipt-", "permission-not-allowed", "not-applicable-")) else "failed"

        after = self.fs.snapshot()
        result = LifecycleResult(
            status=status,
            phases=tuple(phases),
            events=tuple(events),
            trace=tuple(trace),
            mutated=after != before,
            rolled_back=rolled_back,
            safe_checkpoint=safe_checkpoint,
            checkpoint_mode=scenario["protocol"]["checkpoint_mode"],
            receipt=receipt,
            state_sha256=hashlib.sha256(after).hexdigest(),
            error=error,
        )
        self._assert_expected(scenario, result)
        return result

    @staticmethod
    def _ids(rng: random.Random) -> dict[str, str]:
        return {
            "request_id": f"req_{rng.getrandbits(128):032x}",
            "decision_id": f"dec_{rng.getrandbits(128):032x}",
            "run_id": f"run_{rng.getrandbits(128):032x}",
            "plan_id": f"pln_{rng.getrandbits(128):032x}",
            "bundle_id": f"bnd_{rng.getrandbits(128):032x}",
        }

    @staticmethod
    def _event(phase: str, sequence: int, clock: str, ids: dict[str, str], parent: str | None) -> dict[str, Any]:
        event_types = {
            "routing": "route.decided", "validation": "validation.completed",
            "execution": "execution.started", "checkpoint": "checkpoint.recorded",
            "receipt": "receipt.recorded", "outcome": "outcome.recorded",
        }
        correlation = {k: ids[k] for k in ("request_id", "decision_id", "plan_id", "run_id", "bundle_id")}
        if parent:
            correlation["parent_event_id"] = parent
        return {
            "schema_version": "1.0.0",
            "event_id": f"evt_{canonical_sha256({'phase': phase, 'sequence': sequence, **ids})[:32]}",
            "event_type": event_types[phase],
            "occurred_at": clock,
            "sequence": sequence,
            "producer": {"component": "lifecycle-simulator", "version": "1.0.0"},
            "correlation": correlation,
            "privacy": {"classification": "telemetry-sanitized", "content_policy": "metadata-only", "retention_class": "ephemeral", "redactions_applied": []},
            "payload": {"phase": phase, "simulated": True},
        }

    def _assert_expected(self, scenario: dict[str, Any], result: LifecycleResult) -> None:
        expected = scenario["expected"]
        actual_state = json.loads(self.fs.snapshot())
        mismatches = []
        if result.status != expected["status"]:
            mismatches.append(f"status={result.status!r}")
        if result.mutated != expected["mutated"]:
            mismatches.append(f"mutated={result.mutated!r}")
        if actual_state != expected["final_state"]:
            mismatches.append("final_state")
        if mismatches:
            raise AssertionError("scenario expectation mismatch: " + ", ".join(mismatches))

    @staticmethod
    def _receipt(scenario: dict[str, Any], rng: random.Random, ids: dict[str, str]) -> tuple[dict[str, Any], dict[str, Any]]:
        contract_ids = {k: ids[k] for k in ("decision_id", "run_id", "plan_id", "bundle_id")}
        protocol_pin = {
            "kind": "protocol",
            "id": scenario["protocol"]["id"],
            "version": "1.0.0",
            "schema_version": "1.0.0",
            "content_sha256": canonical_sha256(scenario["protocol"]),
        }
        bundle = {
            **contract_ids,
            "protocol_id": scenario["protocol"]["id"],
            "protocol_pin": protocol_pin,
            "variable_pins": [],
        }
        bundle["bundle_sha256"] = canonical_sha256(bundle)
        receipt = {
            "receipt_id": f"rcp_{rng.getrandbits(128):032x}",
            "schema_version": "1.0.0",
            **contract_ids,
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
