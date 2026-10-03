---
schema_version: 1
id: classic-converter-app
name: Classic StoryMap to ArcGIS StoryMaps Converter
domain: work
confidential: false
state: active
health: green
priority: 5
next_action: Verify the Netlify deployment after the requirements update.
updated: 2026-10-03
extra:
  agents: [claude, copilot-enterprise]
  role: Historical reference
  canonical_repository: https://github.com/dasbury-esri/ArcGIS-StoryMaps-Classic-Converter-App
---

# Classic StoryMap to ArcGIS StoryMaps Converter

Converts Classic ArcGIS StoryMaps into the current ArcGIS StoryMaps format
through Python conversion logic and a Vite-based web application.

## Current state

This repository is retained as historical reference. Current development and
project tracking continue in
[ArcGIS-StoryMaps-Classic-Converter-App](https://github.com/dasbury-esri/ArcGIS-StoryMaps-Classic-Converter-App).
The canonical project's status and next action live there. The work registry
retains the immutable `classic-converter-app` ID but resolves the newer repo.

All code, branches, and git history here are preserved. The existing state,
health, priority, and next-action fields are retained as historical values;
the owner requested a historical label rather than a state change. They do
not describe the current canonical project's health or priority.

## Done

- [x] Implemented the initial Classic StoryMap conversion paths.
- [x] Added the Vite converter application and ArcGIS Online OAuth flow.

## Next

- [ ] Follow current work in the canonical repository; consult this repository
  only for historical implementations and experiments.

See `session-logs/` for the manager-readable record of each session.
