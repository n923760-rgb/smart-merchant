#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

REQUIRED = [
    "task_id", "task_type", "task_packet_ref", "executor", "execution_environment",
    "repository", "official_branch", "verified_remote_official_head",
    "exact_tested_head", "authorized_actions", "actions_actually_performed",
    "validation", "facts", "inferences", "assumptions", "residual_risks",
    "recommended_next_action",
]

STATUSES = {"PASS", "FAIL", "BLOCKED", "SKIPPED", "NOT RUN"}
ACTION_RE = re.compile(r"^[a-z][a-z0-9_:-]*$")
PLACEHOLDERS = {"tbd", "none", "n/a", "na", "unknown"}


def fail(message: str, code: int = 1) -> None:
    print(f"INVALID: {message}", file=sys.stderr)
    raise SystemExit(code)


def require_string_list(data: dict, key: str) -> list[str]:
    value = data.get(key)
    if not isinstance(value, list):
        fail(f"{key} must be an array")
    for item in value:
        if not isinstance(item, str):
            fail(f"{key} must contain only strings")
    return value


def require_action_list(data: dict, key: str) -> list[str]:
    value = require_string_list(data, key)
    if len(value) != len(set(value)):
        fail(f"{key} must not contain duplicates")
    for action in value:
        if not ACTION_RE.fullmatch(action):
            fail(f"{key} contains invalid action name: {action!r}")
    return value


def meaningful_evidence(items: object) -> bool:
    if not isinstance(items, list) or not items:
        return False
    for item in items:
        if (
            not isinstance(item, str)
            or not item.strip()
            or item.strip().lower() in PLACEHOLDERS
        ):
            return False
    return True


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: validate-result-packet.py <packet.json>", 2)
    path = Path(sys.argv[1])
    if not path.is_file():
        fail(f"file not found: {path}", 2)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"cannot parse JSON: {exc}")

    missing = [key for key in REQUIRED if key not in data or data[key] in (None, "")]
    if missing:
        fail("missing required fields: " + ", ".join(missing))

    for key in ("verified_remote_official_head", "exact_tested_head"):
        value = str(data[key])
        if not re.fullmatch(r"[0-9a-fA-F]{7,64}", value):
            fail(f"{key} must look like a Git SHA")

    authorized = require_action_list(data, "authorized_actions")
    performed = require_action_list(data, "actions_actually_performed")
    outside = sorted(set(performed) - set(authorized))
    if outside:
        fail("actions actually performed exceed authorization: " + ", ".join(outside))

    validations = data.get("validation")
    if not isinstance(validations, list) or not validations:
        fail("validation must be a non-empty array")

    for index, item in enumerate(validations):
        if not isinstance(item, dict):
            fail(f"validation[{index}] must be an object")
        check = item.get("check")
        status = item.get("status")
        if not isinstance(check, str) or not check.strip():
            fail(f"validation[{index}].check is required")
        if status not in STATUSES:
            fail(f"validation[{index}].status is invalid: {status!r}")

        if status in {"PASS", "FAIL", "BLOCKED"} and not meaningful_evidence(item.get("evidence")):
            fail(f"validation[{index}] with status {status} requires meaningful evidence")

        if status in {"BLOCKED", "SKIPPED", "NOT RUN"}:
            reason = item.get("reason")
            if not isinstance(reason, str) or not reason.strip():
                fail(f"validation[{index}] with status {status} requires a reason")

    for key in ("facts", "inferences", "assumptions", "residual_risks"):
        require_string_list(data, key)

    next_action = data.get("recommended_next_action")
    if not isinstance(next_action, str) or not next_action.strip():
        fail("recommended_next_action must be a non-empty string")

    print("VALID: result packet passes authority and evidence checks")


if __name__ == "__main__":
    main()
