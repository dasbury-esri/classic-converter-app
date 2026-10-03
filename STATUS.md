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
---

# Classic StoryMap to ArcGIS StoryMaps Converter

Converts Classic ArcGIS StoryMaps into the current ArcGIS StoryMaps format
through Python conversion logic and a Vite-based web application.

## Current state

The repository contains API-based and JSON-to-JSON conversion paths plus a web
application. Recent commits adjusted the project for Netlify deployment and
updated its requirements; deployment behavior has not yet been independently
verified in this onboarding session.

## Done

- [x] Implemented the initial Classic StoryMap conversion paths.
- [x] Added the Vite converter application and ArcGIS Online OAuth flow.

## Next

- [ ] Verify the Netlify deployment after the requirements update.

See `session-logs/` for the manager-readable record of each session.