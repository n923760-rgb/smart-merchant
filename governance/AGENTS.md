# Engineering Governance Instructions

Applies to governance/ and to agents explicitly initialized through START_HERE.md.
Preserve root AGENTS.md exactly; it contains the merchant-specific safety rules.

1. Current owner instruction.
2. Root AGENTS.md and applicable scoped repository instructions.
3. Subsystem and environment contracts.
4. Pinned Master Engineering System and current exact task packet.

Before each task verify actual tools, repository, official main HEAD, task HEAD, open PRs and scope. Historical checkpoints are not live authority.
Read ENGINEERING/MASTER_ROADMAP.md after checking live state.
One bounded outcome, one branch, one PR; one source writer.
Read-only diagnosis does not authorize edits.
No direct main writes, force pushes or protected actions without explicit owner authority.
Report PASS / FAIL / BLOCKED / UNKNOWN / NOT RUN / SKIPPED truthfully.
A packet validator checks recorded authority; it does not grant GitHub permissions or prove live source.
Stop on a source mismatch, conflicting PR, unclear authority, missing required capability/evidence, secret exposure or scope expansion.
