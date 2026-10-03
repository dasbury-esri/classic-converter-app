# Agent rules

Canonical agent-rules file for this repository. It binds every agent working
here (GitHub Copilot, and Claude where `STATUS.md` lists it under
`extra.agents`). Copilot reads `.github/copilot-instructions.md`; give Claude
a one-line `CLAUDE.md` containing `@AGENTS.md` if it works here.

Stable rules only. What is true now lives in `STATUS.md`. Do not copy volatile
facts in here.

## Where the rules live

- **Tracking contract** (`STATUS.md` fields, session logs, session closure,
  boundary, repo-relative paths): `.github/copilot-instructions.md`. It
  applies to every agent, not only Copilot.
- **Project conventions** (document roles, OS-agnostic paths): `CONVENTIONS.md`.
- **Local decisions**: `docs/decisions/` — immutable once active.

---

<!-- ADR-015 -->
## Verify before you report (ADR-015 — GLOBAL)

**Never trust a claim that rests solely on code written by yourself or an agent.**
A method cannot audit itself. Until something independent agrees — a separate
artefact, a tool we did not write, a different code path, a semantic check, or
the owner's eyes — a result is a hypothesis, not a finding, and is never
recorded as established. Where nothing independent exists, say so in the same
breath. Unknown defaults to suspect. Destructive actions need independent
evidence, not a passing check.

Full text: `project-tracking/docs/resources/agent-global-rules.md`
Reasoning: `homelab-ops/docs/decisions/ADR-015-verify-before-you-report.md`
<!-- /ADR-015 -->
