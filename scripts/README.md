# scripts

Project-specific scripts live here, plus the bundled **STATUS.md validation
hook** so this repo can validate its own `STATUS.md` at commit time without
depending on the project-tracking clone (it is on the other side of the
work/personal boundary).

## STATUS.md validation hook

| File | Role |
|---|---|
| `validate_status.py` | Validates a `STATUS.md` against `../schema/status-v1.yaml`. Run directly, or via the hook. |
| `hooks/pre-commit` | Blocks a commit that stages an invalid `STATUS.md`. Degrades to a warning (allows the commit) if Python/PyYAML or the schema is missing. |
| `install-hooks.sh` | Copies `hooks/*` into `.git/hooks/`. Run **once per clone**. |

Install:

```bash
scripts/install-hooks.sh    # once per clone; needs Python 3 + PyYAML
```

After install, a commit that stages a `STATUS.md` with placeholder `[OWNER: ...]`
values in `state`/`health` is blocked until those are filled — an intentional
forcing function.

## Snapshot note

`validate_status.py`, `hooks/pre-commit`, `install-hooks.sh`, and
`../schema/status-v1.yaml` are **snapshots** copied from the project-tracking
system at `schema_version: 1`. They are duplicated here on purpose (the boundary
prevents referencing the originals). When the schema version bumps, re-sync
these four files from the canonical work-repo template.
