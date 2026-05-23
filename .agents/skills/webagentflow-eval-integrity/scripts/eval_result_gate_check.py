#!/usr/bin/env python3
"""Conservatively derive an eval integrity decision from JSON results.

Exit codes:
  0: PASS
  1: FAIL or UNVERIFIED
  2: BLOCKED
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PASS_VALUES = {"pass", "passed", "success", "ok"}
FAIL_VALUES = {"fail", "failed", "error"}
BLOCKED_VALUES = {"blocked", "blocker"}
UNVERIFIED_VALUES = {"unverified", "unknown", "warning", "warn", "skipped", "pending"}


def _norm(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _status_of(obj: Any) -> str:
    if isinstance(obj, dict):
        for key in ("status", "result", "pass_gate", "decision", "outcome"):
            if key in obj:
                value = obj[key]
                if isinstance(value, dict):
                    nested = _status_of(value)
                    if nested:
                        return nested
                return _norm(value)
    return _norm(obj)


def _iter_cases(data: dict[str, Any]) -> list[tuple[str, Any]]:
    for key in ("case_results", "cases", "required_cases", "results"):
        value = data.get(key)
        if isinstance(value, dict):
            return list(value.items())
        if isinstance(value, list):
            cases = []
            for index, item in enumerate(value):
                name = item.get("name") if isinstance(item, dict) else None
                cases.append((str(name or index), item))
            return cases
    return []


def _iter_gates(data: dict[str, Any]) -> list[tuple[str, Any]]:
    for key in ("required_gates", "gates", "gate_results", "checks"):
        value = data.get(key)
        if isinstance(value, dict):
            return list(value.items())
        if isinstance(value, list):
            gates = []
            for index, item in enumerate(value):
                name = item.get("name") if isinstance(item, dict) else None
                gates.append((str(name or index), item))
            return gates
    return []


def decide(data: dict[str, Any]) -> dict[str, Any]:
    top_status = _status_of(data)
    issues: list[dict[str, str]] = []

    if top_status in BLOCKED_VALUES:
        return {"decision": "BLOCKED", "reason": "top-level status is blocked", "issues": []}
    if top_status in FAIL_VALUES:
        return {"decision": "FAIL", "reason": "top-level status is fail", "issues": []}
    if top_status in UNVERIFIED_VALUES:
        return {"decision": "UNVERIFIED", "reason": "top-level status is unverified", "issues": []}

    cases = _iter_cases(data)
    gates = _iter_gates(data)

    for group_name, items in (("case", cases), ("gate", gates)):
        for name, item in items:
            status = _status_of(item)
            required = True
            if isinstance(item, dict) and item.get("required") is False:
                required = False
            if not required:
                continue
            if status in BLOCKED_VALUES:
                issues.append({"kind": group_name, "name": name, "status": "BLOCKED"})
            elif status in FAIL_VALUES:
                issues.append({"kind": group_name, "name": name, "status": "FAIL"})
            elif status in UNVERIFIED_VALUES or not status:
                issues.append({"kind": group_name, "name": name, "status": "UNVERIFIED"})
            elif status not in PASS_VALUES:
                issues.append({"kind": group_name, "name": name, "status": f"UNVERIFIED:{status}"})

    if any(issue["status"] == "BLOCKED" for issue in issues):
        return {"decision": "BLOCKED", "reason": "required gate/case is blocked", "issues": issues}
    if any(issue["status"] == "FAIL" for issue in issues):
        return {"decision": "FAIL", "reason": "required gate/case failed", "issues": issues}
    if issues:
        return {"decision": "UNVERIFIED", "reason": "required gate/case is missing or ambiguous", "issues": issues}

    if not cases and not gates and top_status not in PASS_VALUES:
        return {"decision": "UNVERIFIED", "reason": "no case/gate evidence and no explicit pass status", "issues": []}

    return {"decision": "PASS", "reason": "all detectable required gates/cases passed", "issues": []}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result_json", help="Eval result JSON file")
    parser.add_argument("--json-output", help="Optional path to write JSON decision")
    args = parser.parse_args()

    path = Path(args.result_json).resolve()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - report as blocked data issue
        result = {"decision": "BLOCKED", "reason": f"failed to read result JSON: {exc}", "issues": []}
    else:
        if not isinstance(data, dict):
            result = {"decision": "BLOCKED", "reason": "result JSON must be an object", "issues": []}
        else:
            result = decide(data)

    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json_output:
        Path(args.json_output).write_text(output + "\n", encoding="utf-8")
    print(output)

    if result["decision"] == "PASS":
        return 0
    if result["decision"] == "BLOCKED":
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
