# Confirmed journal composer — SM-ACC-003

Repository: n923760-rgb/smart-merchant. Diagnosis source: main 282a0b3c26f15b198562ff98942e10828b85c71f, observed 2026-10-07. Task: ENGINEERING/EVIDENCE/journal-composer-task.json. Actor: Codex, sole source writer; distinct same-session review, not independent approval.

Delivered scope: Arabic/English online composer with paginated authorized account selection, exact decimal normalization and balance preview, explicit acknowledgement/confirmation, persisted same-command identity and scoped result lookup. No terminal or shift dependency. Existing ledger/posting/audit/database protection remain unchanged.

Security prerequisite SM-SEC-008 (PR #18, b66d3091278c4d02858c6e0b0febcc0d61a0f314) is integrated in the candidate tree. Its four prerequisite files are not composer scope; the composer PR initially targets that branch and can move to main after its qualified merge.

Local validation on the security-integrated candidate: npm ci, lint, typecheck, 113 unit tests in 12 files, production build, zero-vulnerability npm audit, task/governance validators, e2e syntax and whitespace checks PASS. Backend static/runtime and real browser qualification remain source-specific CI gates.

Current runtime evidence is attached to the accompanying PR on its exact candidate. Historical main's eleven successful checks are not relabeled as candidate qualification. Local Node 24.19.0/npm 11.9.0/Python 3.12.14/Git and isolated checkout are verified; Docker/Flutter/PostgreSQL/Redis are not installed locally. Required financial integration and real-browser runtime are performed by existing GitHub Actions on disposable services.

Validation includes malformed/large/exact monetary values and dates; independent scoped posting permissions; saving before dispatch; no dispatch on storage/context failure; network loss and restored command identity; absence versus confirmed outcome; matching result verification; explicit identical resend; first definite rejection versus later uncertain rejection; corruption/tenant/user/branch isolation; nonblocking cross-tab command locks and double clicks. Backend tests check request lookup's read-only effect, tenant/branch isolation, independent read permission and suspended membership. Real-ledger browser tests create a real journal and deliberately hide its successful response, reload and recover with GET; a separate pre-dispatch outage observes 404 and resends the identical body/UUID.

Online pending data is minimal browser-local financial content, not credentials or encrypted storage. Clearing a browser profile/device loss can lose its recovery record. Unresolved conflicts remain frozen for investigation; no silent discard or new-ID retry is exposed. Separate independently confirmed UUIDs are distinct operations. Full offline/fiscal/physical/pilot/production acceptance is NOT RUN.

Root AGENTS.md is preserved. No permission defaults, database migrations, numeric policy, production infrastructure, secrets or unrelated generated assets are intentionally changed. Required Foundation, Governance and Accounting Web checks must succeed on the exact final candidate before the owner-authorized merge.

Next bounded task after qualification: account hierarchy, accounting periods and opening balances; reversal controls remain separate, followed by customers/suppliers and a complete service-invoice/settlement/report journey. Review recommendations are recorded as sequenced backlog in the sole canonical roadmap.
