---
mode: agent
description: Scaffold or update this project's STATUS.md to the project-tracking schema (v1).
---

Create or update the `STATUS.md` at the repo root so it conforms to the
project-tracking conventions in `.github/copilot-instructions.md`
(`schema_version: 1`).

Rules:

- Frontmatter fields and their allowed values are defined in
  `.github/copilot-instructions.md`. Use them exactly; do not invent fields.
- `domain` is `work`. `schema_version` is `1`.
- Set `updated` to today's date.
- You MAY set `id` (only if empty — it is immutable once set), `name`,
  `confidential` (default `false`), and anything under `extra` (e.g. `role`,
  `phase`).
- You MUST NOT fabricate the owner-meaningful fields `state`, `health`,
  `priority`, `next_action`. If they are unset, leave the `[OWNER: ...]`
  placeholder for the owner to fill.
- After the frontmatter, keep the `## Current state`, `## Done`, and `## Next`
  sections. Rewrite `## Current state` so it describes the project **as it is
  now** — it replaces the prose, it is not a changelog entry.

If you are unsure of a value, leave the `[OWNER: ...]` placeholder rather than
guessing. Then show me the diff.
