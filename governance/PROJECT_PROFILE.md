# Smart Merchant Governance Profile

Status: SOURCE ADOPTED; GOVERNANCE AND PRODUCT QUALIFICATION INCOMPLETE.
Canonical repository: https://github.com/n923760-rgb/smart-merchant
Official/default branch: main. Reverify live HEAD at every task.
Foundation #1 merged on 2026-10-02 at cec4eba1eb07b9ab4b62ca79cb91a808eb3f373d.
Machine-readable profile: project-profile.json.
Root AGENTS.md preserves the merchant instructions exactly.
Roadmap: ENGINEERING/MASTER_ROADMAP.md. Reports/evidence: ENGINEERING/REPORTS/ and ENGINEERING/EVIDENCE/.
Reference: engineering-governance at 641e4f9e45da109257ba1f38752b94604c2e4531.

Architecture: FastAPI/PostgreSQL/Redis, Next.js BFF/admin, Flutter POS/owner shells.
Application and governance CI are external execution; the controller has repository API writes and no local CLI.
The owner's current instruction permits continued development and reviewed merges. Each protected action must still record that real authority, exact source, target and successful required checks; generic prompts do not grant permissions.
Production deployment, signing, physical pilot devices, infrastructure and backup/restore remain unspecified and unqualified.
