<!-- template_version: 3 — bump in project-tracking/docs/templates/work-repo when this file changes (ADR-024 D7); compare against the copy in each work repo -->
# Copilot custom instructions — work project (project-tracking conventions)

These instructions make this repository conform to the **project-tracking**
system so that automated digests and weekly reports are generated consistently
across every project. Follow them whenever you create or update tracking files
(`STATUS.md`, `session-logs/`).

This is a snapshot of the conventions as of **`schema_version: 1`**
(**`template_version: 3`** — see the comment at the top of this file). The
canonical source lives in the owner's personal `project-tracking` repo and
**cannot be reached from here** (see "Boundary" below). If the owner tells you
the schema version has bumped, ask them for the new contract — do not invent
fields.

---

## Boundary — read first

This is a **work-domain** repository. Which tooling may work on it depends on
`confidential` in `STATUS.md` (the owner's confidential-gate decision,
project-tracking ADR-017):

- **`confidential: false`** (a work repo the owner can make public at will):
  it MAY also be cloned, tracked, and automated on the owner's personal
  infrastructure, including by Claude (ADR-017 Layer 2). If `STATUS.md` lists
  `claude` under `extra.agents`, expect commits and session logs from it.
- **`confidential: true`**: work infrastructure and the corporate-approved
  agent only. No personal infrastructure, personal tooling, or Claude.
- **Never**, either way: a GitHub Enterprise (Devtopia) credential, or any
  credential for a `confidential: true` project, on personal infrastructure
  (ADR-017 Layer 1). Never copy Devtopia, Enterprise, or other proprietary Esri
  content into a `confidential: false` repo — it must stay publishable.
- Only the owner sets or changes `confidential`.
- **Never** add credentials, machine paths, hostnames, or links pointing at the
  owner's personal infrastructure (Nextcloud, personal machines, personal
  GitHub). Personal tooling may *work on* a non-confidential repo; the repo's
  content still must not *depend on or expose* that tooling.
- All tracking conventions you need are embedded **in this file** — you do not
  need (and cannot get) anything from the personal repo at runtime.
- **Onboarding into the registry is not your job.** Registering this project in
  the work registry happens manually from an approved project-tracking authoring
  surface. Do not create or edit any registry file here.

---

## `STATUS.md` — the project's machine-readable state

Every project has exactly one `STATUS.md` at the repo root with a YAML
frontmatter block followed by prose. The frontmatter contract for
`schema_version: 1`:

| field | type | rules |
|---|---|---|
| `schema_version` | integer | `1` for this template. Do not change unless the owner says so. |
| `id` | string | Stable slug. **Immutable** — never changes, even on rename. Set once; if it's already filled, leave it. |
| `name` | string | Display name. May change freely. |
| `domain` | enum | `work` for this repo. Never `personal`. |
| `confidential` | boolean | `true` means hand-entered, never machine-synced. Leave as the owner set it. |
| `state` | enum | one of `active`, `paused`, `blocked`, `done`, `archived`. **Owner-meaningful — never fabricate** (see below). |
| `health` | enum | one of `green`, `yellow`, `red`. **Owner-meaningful.** |
| `priority` | integer | Owner-defined ordinal. **Owner-meaningful.** |
| `next_action` | string | One line: the next concrete step. **Owner-meaningful.** |
| `updated` | string | `YYYY-MM-DD`. Set to today's date whenever you change `STATUS.md`. |
| `extra` | object | Open, unvalidated block. Project-specific fields (e.g. `role`, `phase`) go here. Safe to add to. |

### Owner-meaningful fields — never fabricate

`state`, `health`, `priority`, and `next_action` describe the owner's judgement
of the project. **Do not guess or invent them.** When scaffolding, leave the
placeholder syntax `[OWNER: ...]` in place for the owner to fill. The repo's
pre-commit hook will block a commit while these placeholders remain — that is
intended: it forces the owner to set them before the first real commit.

Fields you *may* set yourself: `id` (once, if empty), `name`, `domain`,
`confidential` (default `false` unless told otherwise), `updated`, and anything
under `extra`.

---

## Session logs — the manager-readable record

Substantive work sessions get a log under `session-logs/`, named
`YYYY-MM-DD-NNNN-session-log.md` where `NNNN` is the next integer after the
highest existing log number (zero-padded to 4 digits, e.g. `0007`).

Use `session-logs/SESSION-LOG-TEMPLATE.md` as the structure. Write in **past
tense**, in terms a **manager could read directly** — these entries are quoted
verbatim in weekly reports. Good: "Fixed the community-tools export — it was
silently dropping the last record." Bad: "fixed the thing."

---

## Workflow expectations

- Keep `STATUS.md` honest: when work changes the project's real state, bump
  `updated` and rewrite the `## Current state` prose so it describes the
  project **as it stands now** (it replaces the old prose; it is not a
  changelog). Update `next_action` / `extra.phase` to match.
- Your planning files under `.github/prompts/` are yours to manage; they do not
  feed the digest.
- Degrade, don't break: if you're unsure of an owner-meaningful value, leave
  the `[OWNER: ...]` placeholder rather than guessing.

## Session closure requirements (mandatory)

A session is not complete until one of the closure paths below is finished.

### Session type classification

- **Substantive session**: any session that changes project artifacts,
  decisions, implementation, documentation, plans, or repository state.
- **Minor/no-change session**: a quick check-in, read-only review, or planning
  interaction that does not change repository files.

When uncertain, treat the session as **substantive**.

### Required closure for substantive sessions

1. Write a new session log in `session-logs/` using the required naming
   convention and `SESSION-LOG-TEMPLATE.md` structure.
2. Update `STATUS.md` so it reflects the current project reality:
   - set `updated` to today's date,
   - rewrite `## Current state` in replacement (not changelog) form,
   - update `next_action` and `extra.phase` as needed.
3. Stage and commit closure changes, including:
   - the new session log,
   - `STATUS.md`,
   - any other files changed during the session.
4. Push the commit to GitHub on the active working branch.

### Required closure for minor/no-change sessions

1. If no repository files changed, do not create an empty commit.
2. If `STATUS.md` and session logs remain accurate, no tracking-file edits are
   required.
3. If any file did change, reclassify as **substantive** and follow the
   substantive closure path above.

### Enforcement behavior

- Do not report a substantive session as complete before commit and push
  succeed.
- If commit or push fails, stop and report the exact blocker and required user
  action.
- Do not invent owner-meaningful values (`state`, `health`, `priority`,
  `next_action`); leave placeholders when owner input is unavailable.

### Commit message convention

For substantive closure commits, prefer:

`chore(session): close session with status and log updates`

---

## Paths — repo-relative, never machine-absolute

When you write a path into any file (`STATUS.md`, session logs, your own
planning files under `.github/prompts/`), make it **repo-relative**:
`docs/resources/foo.md`, not `/Users/you/srv/.../docs/resources/foo.md` and not
`C:\...`. These repos are cloned on Mac, Windows, and Linux; an absolute machine
path resolves on exactly one of them and is broken everywhere else.

<!-- ADR-015 -->
## Verify before you report (ADR-015 — GLOBAL, binds every agent and the owner)

**Never trust a claim that rests solely on code written by yourself or an agent.**
A script one of us wrote is part of the method; a method cannot audit itself.
Until something independent agrees, a result is a hypothesis — usable, but never
written into a document, registry, or commit message as established fact.

**Verification must come from outside the method:** a physically separate
artefact, a tool we did not write (`md5sum`, `rsync --checksum`, `file`,
`smartctl`, `e2fsck -n`), a different code path reading the same thing, a
semantic check sharing no logic with the claim, or the owner's own eyes.
Re-running the same script is not verification. Nor is a second function inside it.

**Where nothing independent exists, say so in the same breath as the claim.**

**Unknown defaults to suspect, never to good.** An optimistic default converts
ignorance into false assurance, and does it hardest where checking is hardest.

**Destructive actions require independent evidence, not a passing check.**

Why this exists: an extraction once reported every file at the exact expected
path and size while 29% of it was garbage, and a classifier then under-reported
a data loss by 599 files. Both agreed with themselves completely. Full account:
`homelab-ops/docs/decisions/ADR-015-verify-before-you-report.md`.
<!-- /ADR-015 -->
