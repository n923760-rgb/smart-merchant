# Start a governed development session

Reference: [Master Engineering System](https://github.com/n923760-rgb/engineering-governance/blob/641e4f9e45da109257ba1f38752b94604c2e4531/MASTER_GOVERNANCE.md).
Pinned source: 641e4f9e45da109257ba1f38752b94604c2e4531; reviewed unreleased main snapshot, not a claim about the immutable v1.0.0 release.
This project adopts its own facts and preserves candidate merchant instructions byte-for-byte in root AGENTS.md.

## Start
Tell your coding agent:
> Read AGENTS.md, governance/AGENTS.md, governance/PROJECT_PROFILE.md, governance/ENGINEERING_ENVIRONMENT_CONTRACT.md and ENGINEERING/MASTER_ROADMAP.md. Verify live repository and PR state. Act using governance/agents/controller.md. Report capabilities and choose the next bounded task from current evidence.

Use an authorized CLI/coding-agent environment for application implementation. The current API session has no shell.
These instructions configure agent behavior; they do not install a hosted model, persistent worker, GitHub App or scheduled autonomous execution.

## Work cycle
1. Controller defines one exact-source task and allowed actions.
2. Executor validates the packet, performs live checks and owns the only source writes.
3. Executor returns attributable validation and a result packet.
4. Reviewer checks the complete diff and evidence; controller reconciles the single roadmap.
5. Reconcile protected actions with current explicit owner instructions. The owner has authorized continued development and merges; do not request the same authorization again. Verify exact source and required evidence before each merge.

Validate actual packets using:
```sh
python governance/tools/validate-task-packet.py path/to/task.json
python governance/tools/validate-result-packet.py path/to/result.json
```
The baseline packets under ENGINEERING/EVIDENCE are historical records, never reusable execution authorization.
GitHub Governance CI checks contracts and negative authority/evidence fixtures. It does not run the application.
Foundation PR #1 is merged into main. Reverify live main and task heads before application work; historical SHA values are not live execution authority.
