# Architecture Decision Records (ADRs)

An ADR records a decision: what was decided, why, and what it implies — the
reasoning, not just the outcome. This directory holds **local** ADRs: decisions
specific to *this* project.

Global, cross-project decisions (the work/personal boundary, the STATUS
contract, the registry, etc.) live in the project-tracking system's
`docs/decisions/`. Reference them by URL where relevant — **never copy a global
ADR's content into this repo.**

## Sections

Every ADR has four sections (see `ADR-TEMPLATE.md`):

- **Status** — one of `proposed`, `active`, `superseded`.
- **Context** — the situation and reasoning that led to the decision. Rationale
  lives here; don't flatten it to a one-liner.
- **Decision** — what was decided, stated plainly.
- **Consequences** — what this implies, enables, or rules out, including
  trade-offs accepted.

## Status values

- **proposed** — under consideration, not yet binding.
- **active** — in force. The current rule.
- **superseded** — replaced by a later ADR. The record stays; it is never
  deleted or edited. The superseding ADR is linked.

## Rules

- ADRs are immutable once `active` as to their decisions and reasoning. To change
  a decision, write a new ADR that supersedes the old one — don't edit the old.
- Mechanical corrections that alter no decision text (a moved-file path, a typo)
  are permitted on an active ADR and noted in that session's log.
- Numbering is sequential (ADR-000, ADR-001, ...) and never reused.
- Update the index below whenever a new ADR is written, so it never goes stale.

## Index

_(No local ADRs yet. Add the first as `ADR-000-<slug>.md` and list it here.)_
