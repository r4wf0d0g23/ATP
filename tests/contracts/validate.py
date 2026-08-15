#!/usr/bin/env python3
import json
import pathlib
import sys

import jsonschema

ROOT = pathlib.Path(__file__).resolve().parents[2]
cases = json.loads((ROOT / "tests/contracts/cases.json").read_text())
failed = []
for case in cases:
    schema = json.loads((ROOT / case["schema"]).read_text())
    fixture = json.loads((ROOT / case["fixture"]).read_text())
    try:
        jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker()).validate(fixture)
        actual = True
    except jsonschema.ValidationError:
        actual = False
    if actual != case["valid"]:
        failed.append(f'{case["fixture"]}: expected valid={case["valid"]}, got {actual}')

if failed:
    print("\n".join(failed), file=sys.stderr)
    sys.exit(1)
print(f"contract fixtures passed: {len(cases)}")
