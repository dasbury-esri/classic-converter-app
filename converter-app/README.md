# Classic StoryMap Converter Web App

A client-side web application for converting Classic ArcGIS StoryMaps (MapJournal, MapSeries, Cascade) to ArcGIS StoryMaps format.

> **📚 For general project information, Python converters, and conversion logic details, see the [main README](../README.md).**

## Features

- **Client-side conversion**: Runs entirely in the browser, no backend required
- **ArcGIS authentication**: Uses existing ArcGIS Online session via `esri_aopc` cookie
- **REST API integration**: Direct calls to ArcGIS REST API endpoints
- **TypeScript conversion logic**: Ported from Python `converter_json.py`
- **Automatic image transfer**: Downloads images from classic story resources and uploads to target story
- **Updates existing drafts**: Replaces draft resource JSON in target storymap

## Quick Start

```powershell
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## How It Works

1. User signs in to ArcGIS Online (in any browser tab)
2. User manually copies their ArcGIS Online token from the 'traffic' network request in browser DevTools
3. User provides:
   - **Classic Story Item ID**: The source classic story to convert
   - **Target StoryMap Draft ID**: An existing draft storymap to update
4. App fetches classic story data via ArcGIS REST API
5. Converts JSON structure client-side using TypeScript
6. **Transfers images**: Downloads images from classic story resources and uploads to target story
7. Updates JSON with new image URLs
8. Finds draft resource name from target item (e.g., `draft_1760457248004.json`)
9. Removes old draft resource
10. Uploads new converted draft resource with same name
11. Adds `smconverter:online-app` keyword to target item

## Architecture

### `/src/converter/` - Conversion Logic

- `storymap-schema.ts` - Node and resource creators
- `storymap-builder.ts` - JSON builder class
- `journal-converter.ts` - MapJournal/MapSeries converter
- `cascade-converter.ts` - Cascade converter
- `converter-factory.ts` - Converter selector
- `utils.ts` - Shared utilities (HTML parsing, scale calculations)

### `/src/api/` - ArcGIS REST API Client

- `arcgis-client.ts` - Functions for fetching item data, resources, and updating items
- `image-transfer.ts` - Image download/upload utilities for preserving classic story images

### `/src/auth/` - Authentication

- `auth.ts` - Token management utilities (session storage)

**Note on Authentication:** Due to browser Same-Origin Policy, the app running on `localhost` cannot read cookies from `arcgis.com`. Users must manually copy their token from browser DevTools.

### `/src/components/` - React UI

- `Converter.tsx` - Main conversion interface component

### `/src/types/` - TypeScript Types

- `storymap.d.ts` - Interface definitions for StoryMap JSON structures

## Visual Documentation

For detailed conversion flow diagrams, see [DIAGRAMS.md](./DIAGRAMS.md).

The diagrams include:

- High-level TypeScript conversion flow
- StoryMapJSONBuilder architecture
- Journal/Series converter processing
- Journal/Series content element handling
- Cascade converter processing
- Cascade block type dispatching
- Utility functions (removeSpanTags, parseHtmlText, scale calculations)

## Prerequisites

- User must be signed in to ArcGIS Online
- Classic story must be accessible with user's credentials
- Target storymap must exist as a draft
- User must have edit permissions on target storymap

## REST API Endpoints Used

- `GET /sharing/rest/content/items/{id}/data` - Fetch classic story data
- `GET /sharing/rest/content/items/{id}` - Get item details
- `GET /sharing/rest/community/self` - Get username
- `POST /sharing/rest/content/users/{user}/items/{id}/removeResources` - Remove draft
- `POST /sharing/rest/content/users/{user}/items/{id}/addResources` - Add draft
- `POST /sharing/rest/content/users/{user}/items/{id}/update` - Update keywords

## Development

Built with:

- **React 19** - UI framework
- **TypeScript 5.9** - Type safety
- **Vite 7** - Build tool and dev server

## Notes

- No backend/server required - runs entirely in browser
- Uses existing ArcGIS authentication (no separate login)
- Preserves target storymap item ID (updates in place)
- Adds tracking keyword: `smconverter:online-app`
- **Image handling**: Automatically transfers images from classic story resources to target story
- **Schema compatibility**: Output matches Python converter exactly (verified against test data)
- **HTML parsing**: Uses immediate children only for caption/image-container elements (matches Python behavior)
