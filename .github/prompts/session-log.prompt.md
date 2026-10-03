---
mode: agent
description: Write a session log for the work just done, in manager-readable form.
---

Write a session log capturing the work from this session into
`session-logs/YYYY-MM-DD-NNNN-session-log.md`.

Steps:

1. Find the highest existing `NNNN` in `session-logs/` and use the next integer,
   zero-padded to 4 digits (e.g. if the highest is `0006`, use `0007`).
2. Name the file `<today's date>-NNNN-session-log.md` using `YYYY-MM-DD`.
3. Use `session-logs/SESSION-LOG-TEMPLATE.md` as the structure.
4. Write in **past tense**, in terms a **manager could read directly** — these
   lines are quoted verbatim in weekly reports. Describe outcomes, not vague
   activity ("Fixed the export that was dropping the last record," not "fixed
   the thing").
5. Fill in only what actually happened. Leave optional sections out if they do
   not apply (e.g. Photos/Supplies for a non-hardware session).

After writing the log, remind me to update `STATUS.md` (use the
`update-status` prompt) if the project's real state changed.
