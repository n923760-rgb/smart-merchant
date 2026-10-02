#!/usr/bin/env python3
"""Validate adopted contracts and recorded authority/evidence rejection.

This does not qualify live Git gates, branch protection or application runtime.
"""
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def validate_contract(document, schema_path):
    schema = load(schema_path)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(document)


def packet_check(tool, packet, accepted):
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / "packet.json"
        path.write_text(json.dumps(packet), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(ROOT / "governance/tools" / tool), str(path)],
            capture_output=True, text=True, check=False,
        )
    if (result.returncode == 0) != accepted:
        raise AssertionError(
            f"{tool}: expected accepted={accepted}, exit={result.returncode}\n"
            + result.stdout + result.stderr
        )


def main():
    profile = load("governance/project-profile.json")
    task = load("ENGINEERING/EVIDENCE/baseline-task.json")
    result = load("ENGINEERING/EVIDENCE/baseline-result.json")
    for document, name in (
        (profile, "project-profile"),
        (task, "task-packet"),
        (result, "result-packet"),
    ):
        validate_contract(document, f"governance/schemas/{name}.schema.json")
    if profile["repository"] != "n923760-rgb/smart-merchant":
        raise AssertionError("Wrong canonical repository")
    if profile["official_branch"] != "main":
        raise AssertionError("Wrong official branch")
    for field in ("repository_authority_file", "master_roadmap",
                  "master_baseline_report", "engineering_lab_contract"):
        path = (ROOT / profile[field]).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            raise AssertionError(f"Missing or escaping project path: {field}")
    if task["repository"] != profile["repository"] or result["repository"] != profile["repository"]:
        raise AssertionError("Packet repository mismatch")
    if result["task_packet_ref"] != "ENGINEERING/EVIDENCE/baseline-task.json":
        raise AssertionError("Result does not identify baseline task")
    if result["verified_remote_official_head"] != task["expected_official_head"]:
        raise AssertionError("Historical result/task baseline mismatch")

    packet_check("validate-task-packet.py", task, True)
    packet_check("validate-result-packet.py", result, True)

    for path in sorted((ROOT / "ENGINEERING/EVIDENCE").glob("*-task.json")):
        packet = json.loads(path.read_text(encoding="utf-8"))
        validate_contract(packet, "governance/schemas/task-packet.schema.json")
        packet_check("validate-task-packet.py", packet, True)
    for path in sorted((ROOT / "ENGINEERING/EVIDENCE").glob("*-result.json")):
        packet = json.loads(path.read_text(encoding="utf-8"))
        validate_contract(packet, "governance/schemas/result-packet.schema.json")
        packet_check("validate-result-packet.py", packet, True)

    bad = copy.deepcopy(task)
    bad["requested_actions"].append("modify")
    packet_check("validate-task-packet.py", bad, False)

    bad = copy.deepcopy(task)
    bad["requested_actions"].append("merge")
    bad["authorized_actions"].append("merge")
    packet_check("validate-task-packet.py", bad, False)

    bad = copy.deepcopy(task)
    bad["expected_pr_head"] = None
    packet_check("validate-task-packet.py", bad, False)

    bad = copy.deepcopy(result)
    bad["validation"][0]["evidence"] = []
    packet_check("validate-result-packet.py", bad, False)

    bad = copy.deepcopy(result)
    bad["actions_actually_performed"].append("production_deploy")
    packet_check("validate-result-packet.py", bad, False)

    print("PASS: profile/packet contracts and authority/evidence rejection fixtures")
    print("NOT RUN: live SHA/dirty tree/conflicting PR/capacity gates or application runtime")


if __name__ == "__main__":
    main()
