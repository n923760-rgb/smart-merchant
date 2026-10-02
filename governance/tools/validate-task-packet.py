#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

REQUIRED = [
    "title", "task_type", "authority", "repository", "official_branch",
    "expected_official_head", "scope", "out_of_scope", "task",
    "validation", "stop_conditions", "success_criteria",
    "requested_actions", "authorized_actions", "protected_actions",
    "protected_action_authorizations",
]

TASK_TYPES = {
    "READ-ONLY DIAGNOSIS",
    "IMPLEMENTATION",
    "RUNTIME QUALIFICATION",
    "CI INVESTIGATION",
    "INFRASTRUCTURE MAINTENANCE",
}

ACTION_RE = re.compile(r"^[a-z][a-z0-9_:-]*$")


def fail(message: str, code: int = 1) -> None:
    print(f"INVALID: {message}", file=sys.stderr)
    raise SystemExit(code)


def require_action_list(data: dict, key: str) -> list[str]:
    value = data.get(key)
    if not isinstance(value, list):
        fail(f"{key} must be an array")
    if len(value) != len(set(value)):
        fail(f"{key} must not contain duplicates")
    for action in value:
        if not isinstance(action, str) or not ACTION_RE.fullmatch(action):
            fail(f"{key} contains invalid action name: {action!r}")
    return value


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: validate-task-packet.py <packet.json>", 2)
    path = Path(sys.argv[1])
    if not path.is_file():
        fail(f"file not found: {path}", 2)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"cannot parse JSON: {exc}")

    missing = [key for key in REQUIRED if key not in data]
    if missing:
        fail("missing required fields: " + ", ".join(missing))

    empty = [
        key for key in REQUIRED
        if key != "protected_action_authorizations" and data[key] in (None, "", [])
    ]
    if empty:
        fail("empty required fields: " + ", ".join(empty))

    if data["task_type"] not in TASK_TYPES:
        fail(f"unsupported task_type: {data['task_type']}")

    existing_pr = data.get("existing_pr")
    expected_pr_head = data.get("expected_pr_head")
    expected_pr_base = data.get("expected_pr_base")
    if existing_pr is not None:
        if not isinstance(existing_pr, int) or isinstance(existing_pr, bool) or existing_pr < 1:
            fail("existing_pr must be a positive integer or null")
        if not isinstance(expected_pr_head, str) or not re.fullmatch(r"[0-9a-fA-F]{7,64}", expected_pr_head):
            fail("expected_pr_head must look like a Git SHA when existing_pr is set")
        if not isinstance(expected_pr_base, str) or not expected_pr_base.strip():
            fail("expected_pr_base is required when existing_pr is set")
    elif expected_pr_head is not None or expected_pr_base is not None:
        fail("expected_pr_head/base must be null when existing_pr is null")

    head = str(data["expected_official_head"])
    if not re.fullmatch(r"[0-9a-fA-F]{7,64}", head):
        fail("expected_official_head must look like a Git SHA")

    requested = require_action_list(data, "requested_actions")
    authorized = require_action_list(data, "authorized_actions")
    protected = require_action_list(data, "protected_actions")

    unauthorized = sorted(set(requested) - set(authorized))
    if unauthorized:
        fail("requested actions are not authorized: " + ", ".join(unauthorized))

    authorizations = data.get("protected_action_authorizations")
    if not isinstance(authorizations, dict):
        fail("protected_action_authorizations must be an object")

    for action in sorted(set(authorized) & set(protected)):
        record = authorizations.get(action)
        if not isinstance(record, dict):
            fail(f"protected action {action} lacks explicit owner authorization")
        if record.get("source") != "CURRENT_OWNER_INSTRUCTION":
            fail(f"protected action {action} must be authorized by CURRENT_OWNER_INSTRUCTION")
        reference = record.get("reference")
        if not isinstance(reference, str) or not reference.strip():
            fail(f"protected action {action} authorization reference is missing")

    extras = sorted(set(authorizations) - (set(authorized) & set(protected)))
    if extras:
        fail(
            "authorization records exist for actions that are not authorized protected actions: "
            + ", ".join(extras)
        )

    print("VALID: task packet passes authority and baseline checks")


if __name__ == "__main__":
    main()
