# Conventions — Classic StoryMap to ArcGIS StoryMaps Converter

This project follows the project-tracking conventions so its `STATUS.md` and
session logs feed digests and weekly reports consistently. The machine-readable
rules Copilot follows live in `.github/copilot-instructions.md`; this file holds
the human-facing conventions.

## Document roles

Each fact has exactly one home; everything else links to it.

- **README.md** — why this project exists, plus a map. Changes rarely. No status, no plans.
- **STATUS.md** — what is true now. Machine-validated; the only file the aggregator reads.
- **docs/decisions/** — local ADRs: what was decided and why. Immutable once active.
- **session-logs/** — what happened, per session. Append-only, manager-readable.

## OS-agnostic paths

Paths written into any tracked file must be **repo-relative and OS-agnostic** so
the same value resolves on Mac, Windows, and Linux. Absolute machine paths —
`/Users/...`, `/home/...`, `C:\...` — are drift, not content. Point at things by
repo-relative path (`docs/resources/foo.md`), not by their location on one machine.

This is a convention, not a machine-enforced check — legitimate absolute paths in
runbooks (e.g. install locations) are fine. The target is cross-machine
references that should resolve everywhere.

## Boundary

This is a **work-domain** repository. Under project-tracking ADR-017, a
`confidential: false` repo may also be worked on by personal tooling (including
Claude); a `confidential: true` repo may not. GitHub Enterprise (Devtopia)
credentials and confidential or proprietary content never reach personal
infrastructure. Either way, the repo's content never references personal
infrastructure (Nextcloud, personal GitHub, personal clone roots). See
`.github/copilot-instructions.md` for the full boundary rule.
