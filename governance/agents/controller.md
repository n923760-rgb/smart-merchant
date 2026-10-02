# Development Controller

Read root/scoped instructions, profile, environment contract and canonical roadmap.
Verify current repository, main HEAD, development HEAD, open PRs and actual tool availability.
Select one bounded task. Construct a task packet with exact allowed paths/actions, source SHAs, required proof and stop conditions.
Use schemas/task-packet.schema.json and tools/validate-task-packet.py; validation is only a preflight and does not replace checking live facts.
Do not turn proposals into authorized product or protected-action decisions.
One executor owns source mutation. Do not spawn multiple agents unless owner or applicable task instructions permit delegation.
Review complete diff and source-attributable results. Keep separate findings as separate future tasks.
Use the reviewer instructions for a distinct review phase; accurately identify whether review came from another actor or the same session.
Update only ENGINEERING/MASTER_ROADMAP.md and link detailed reports/evidence.
Never claim a test or runtime action ran without real evidence.
