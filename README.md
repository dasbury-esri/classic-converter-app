# Classic StoryMap to ArcGIS StoryMaps Converter

A comprehensive tool for converting Classic ArcGIS StoryMaps (MapJournal, MapSeries, and Cascade) to the new ArcGIS StoryMaps format.

## Overview

This project provides three approaches for converting classic stories:

1. **API-Based Conversion** (`converter_v2.py`) - Uses the ArcGIS Python API to create StoryMaps
2. **JSON-to-JSON Conversion** (`converter_json.py`) - Direct JSON transformation without API calls
3. **Client-Side Web App** (`converter-app/`) - TypeScript/React app that converts stories directly in the browser

## Project Structure

```
classic-converter/
├── converter_v2.py              # API-based converter (original)
├── converter_json.py            # JSON-to-JSON converter (Python)
├── storymap_json_schema.py      # JSON schema templates and utilities
├── test_converter.py            # Batch test script
├── example_usage.py             # Usage examples
├── .env.example                 # Example configuration file
├── .gitignore                   # Git ignore rules
├── converter-app/               # TypeScript web app (NEW)
│   ├── src/
│   │   ├── converter/          # TypeScript conversion logic
│   │   │   ├── storymap-schema.ts
│   │   │   ├── storymap-builder.ts
│   │   │   ├── journal-converter.ts
│   │   │   ├── cascade-converter.ts
│   │   │   ├── converter-factory.ts
│   │   │   └── utils.ts
│   │   ├── api/                # ArcGIS REST API client
│   │   │   └── arcgis-client.ts
│   │   ├── auth/               # Authentication utilities
│   │   │   └── auth.ts
│   │   ├── components/         # React components
│   │   │   └── Converter.tsx
│   │   └── types/              # TypeScript type definitions
│   │       └── storymap.d.ts
│   ├── DIAGRAMS.md             # TypeScript conversion flow diagrams (7 diagrams)
│   └── package.json
├── schemas/                     # Official ArcGIS StoryMap schemas
│   ├── embed.json
│   ├── image.json
│   ├── webmap.json
│   └── gallery.json
├── test_data/                   # Test files
│   ├── classics/                # Classic story JSON files
│   └── output/                  # Converted StoryMap JSON (generated)
├── CONVERTER_LOGIC.md           # Detailed logic documentation
├── CONVERTER_LOGIC_DIAGRAM.md   # Visual flowcharts (16 diagrams)
├── IMPROVEMENTS.md              # Identified improvements and future enhancements
└── README.md                    # This file
```

## Supported Classic StoryMap Types

- **MapJournal**: Side panel navigation with main stage media
- **MapSeries**: Tab-based navigation (treated identically to Journal)
- **Cascade**: Scrolling narrative with immersive sections

All types convert to ArcGIS StoryMaps with sidecar layouts:

- Journal/Series → Docked-panel sidecars
- Cascade → Mixed content with floating-panel sidecars for immersive sections

## Requirements

### For API-Based Conversion (converter_v2.py)

```
Python 3.11
arcgis >= 2.1.0.2
beautifulsoup4
```

### For JSON-to-JSON Conversion (converter_json.py)

```
Python 3.11
beautifulsoup4
```

Note: The JSON converter does NOT require the arcgis package, making it more lightweight and portable.

### For Testing (test_converter.py)

```
Python 3.11
beautifulsoup4
arcgis >= 2.1.0.2 (for creating actual StoryMap items)
python-dotenv (optional, for .env file support)
```

## Installation

```powershell
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install all dependencies from requirements.txt
pip install -r requirements.txt

# Or install individually:
pip install arcgis beautifulsoup4 python-dotenv
```

### Configuration

Create a `.env` file in the project root for ArcGIS credentials:

```
GIS_PORTAL=https://www.arcgis.com
GIS_USERNAME=your_username
GIS_PASSWORD=your_password
```

Or leave `GIS_USERNAME` empty to use "home" authentication (ArcGIS Pro).

**Note:** The `.env` file is gitignored for security. Never commit credentials!

## Usage

### API-Based Conversion

Edit the configuration variables at the top of `converter_v2.py`:

```python
classic_story_id = "YOUR_ITEM_ID_HERE"  # Classic story item ID
theme_id = "summit"                      # Theme: summit, obsidian, mesa, ridgeline, tidal, slate
portal = "https://www.arcgis.com"       # Portal URL
username = ""                            # Leave empty to use "home" auth
password = ""
```

Run the converter:

```powershell
python converter_v2.py
```

The script will:

1. Fetch the classic story from ArcGIS
2. Create a new StoryMap with converted content
3. Save as an unpublished draft in your content
4. Print the URL of the new story

### JSON-to-JSON Conversion

```python
from converter_json import convert_classic_to_json, save_json_to_file
import json

# Load classic story JSON
with open('classic_story.json', 'r') as f:
    classic_json = json.load(f)

# Convert to StoryMap JSON
storymap_json = convert_classic_to_json(
    classic_json,
    theme_id="summit",
    gis_token=None  # Optional: for downloading AGO images
)

# Save to file
save_json_to_file(storymap_json, 'new_storymap.json')

# The JSON can then be used to create a StoryMap item via REST API
```

### Testing Conversion

Use the test script to batch-convert and validate multiple stories:

```powershell
# Convert all test files and create actual StoryMap items
python test_converter.py

# Convert to JSON only (no item creation)
python test_converter.py --json-only

# Analyze test data structure
python test_converter.py --analyze
```

The test script will:

1. Load all classic story JSON files from `test_data/classics/`
2. Convert each to StoryMap JSON format
3. Validate against official schemas
4. Create actual ArcGIS StoryMap items (full mode)
5. Generate detailed test report
6. Save outputs to `test_data/output/`

**Configuration:** Uses `.env` file or environment variables for ArcGIS credentials (see Configuration section above).

### Client-Side Web App (TypeScript/React)

The web app provides a user-friendly interface for converting classic stories directly in the browser:

```powershell
# Navigate to the app directory
cd converter-app

# Install dependencies
npm install

# Start development server
npm run dev
```

The app will be available at `http://localhost:5173`

**How it works:**

1. User signs in to ArcGIS Online (in any tab/window)
2. User manually copies their `esri_aopc` token from browser DevTools (cookies)
3. User enters:
   - ArcGIS token (copied from browser)
   - Classic Story Item ID (source)
   - Target StoryMap Draft ID (destination)
4. App fetches classic story data via ArcGIS REST API
5. Converts JSON client-side using TypeScript conversion logic
6. Updates target storymap's draft resource with converted JSON
7. Adds `smconverter:online-app` keyword to track conversions

**Key Features:**

- ✅ No backend required - runs entirely in browser
- ✅ Manual token input (browser Same-Origin Policy prevents automatic cookie reading)
- ✅ Direct REST API calls to ArcGIS Online
- ✅ Same conversion logic as Python version (ported to TypeScript)
- ✅ **Automatic image transfer** - downloads images from classic story and uploads to new story
- ✅ Updates existing draft storymaps (preserves item ID)
- ✅ Minimal UI with clear status messages and token help

**Prerequisites:**

- User must be signed in to ArcGIS Online
- Target storymap must already exist as a draft
- User must have edit permissions on target storymap

## Key Features

### API-Based Converter

- ✅ Fully functional conversion using official API
- ✅ Automatic image downloading and resource management
- ✅ Map extent and layer visibility preservation
- ✅ Theme detection from cascade settings
- ✅ Automatic cleanup of temporary files
- ⚠️ Requires ArcGIS Python API and authentication
- ⚠️ Multiple save/reload cycles for complex stories

### JSON-to-JSON Converter

- ✅ No ArcGIS API dependency
- ✅ Direct JSON transformation
- ✅ Identical output structure to API version
- ✅ Faster processing (no API round-trips)
- ✅ Easier to test and debug
- ⚠️ Requires separate upload step to create item
- ℹ️ Good for batch processing or custom workflows

## Conversion Process

### Journal/Series Conversion

1. Creates empty StoryMap with docked-panel sidecar
2. Iterates through sections/entries
3. For each section:
   - Processes media (map, image, video, webpage)
   - Parses HTML content for narrative
   - Creates slide with media + narrative content
4. Post-processes:
   - Applies map settings (extent, scale, layers)
   - Cleans up resources
   - Sets embed types
   - Applies theme
5. Saves as unpublished draft

### Cascade Conversion

1. Creates empty StoryMap
2. Detects theme from cascade settings
3. Processes sections by type:
   - **Cover**: Sets title, subtitle, cover image
   - **Sequence**: Adds blocks directly to story
   - **Immersive**: Creates floating-panel sidecar with views as slides
   - **Title**: Adds centered heading with optional image
   - **Credits**: (Currently disabled due to API limitations)
4. Cleans up temporary images
5. Applies theme and saves

## Content Mapping

### Media Types

| Classic Type | ArcGIS StoryMap Type | Notes                                     |
| ------------ | -------------------- | ----------------------------------------- |
| WebMap       | Map                  | Preserves extent, scale, layer visibility |
| WebScene     | Map                  | Preserves extent, layer visibility        |
| Image        | Image                | Downloads AGO resources locally           |
| Video        | Embed                | embedlyType: video, display: inline       |
| Webpage      | Embed                | embedlyType: link, display: card          |

### Text Styles

| Classic Tag    | StoryMap Style | Alignment             |
| -------------- | -------------- | --------------------- |
| `<h1>`         | Heading        | Center                |
| `<h2>`         | Subheading     | Center                |
| `<p>`          | Paragraph      | From text-align style |
| `<blockquote>` | Quote          | Center                |

### HTML Cleaning

The converter preserves the following HTML tags:

- `<strong>`, `<em>` (formatting)
- `<ol>`, `<ul>`, `<li>` (lists)
- `<a>` (links)
- `<img>` (images)

All other tags are removed (unwrapped), preserving content.

## Known Issues and Limitations

### Critical Bugs

1. **Line 1164 in converter_v2.py**: Uses global `classic_story_id` instead of `itemid` parameter
2. **Line 1111 in converter_v2.py**: Incorrect boolean logic in type detection
3. **Line 793 in converter_v2.py**: Hardcoded node ID for credits

### API Limitations

1. **Sidecar creation**: Must manually construct node structure (v2.1.0.2)
2. **Video covers**: Not supported in Python API for Cascade covers
3. **Credits section**: Disabled due to API bug (scheduled fix mid-2023)
4. **Map recursive issue**: Requires story reload when processing maps

### Performance Issues

1. Multiple story reloads for map processing (Journal/Series)
2. Sequential image downloads (no parallelization)
3. No resource pre-validation (may fail partway through)

See `IMPROVEMENTS.md` for detailed improvement proposals addressing these issues.

## Documentation

- **CONVERTER_LOGIC.md**: Comprehensive technical documentation of the conversion logic, data flow, and architecture
- **CONVERTER_LOGIC_DIAGRAM.md**: Visual flowcharts showing the conversion process for all story types
- **IMPROVEMENTS.md**: Identified improvements in code organization, performance, and error handling with implementation proposals

## Project Discoveries

### Recent Changes (Latest Session - October 17, 2025)

9. **Fixed Content Duplication Issues** (October 17, 2025 - Late Session)

   - ✅ **Journal/Series Duplication Fixed:** Media and narrative content nodes were being added to both the sidecar slides AND the story root
   - ✅ **Cascade Immersive Duplication Fixed:** Text, images, and other content in immersive sections were being added to both the narrative panels AND the story root
   - ✅ **Solution:** Created detached node methods in StoryMapJSONBuilder:
     - `addTextDetached()` - Creates text nodes without adding to story root
     - `addImageDetached()` - Creates image nodes without adding to story root
     - `addMapDetached()` - Creates map nodes without adding to story root
     - `addEmbedDetached()` - Creates embed nodes without adding to story root
     - `addGalleryDetached()` - Creates gallery nodes with detached images
   - ✅ **Implementation:**
     - Journal/Series: All sidecar content (media + narrative) uses detached methods
     - Cascade: All immersive narrative content uses detached methods via `returnIdOnly` flag
     - Cascade: Updated `processTextBlock()`, `processImageBlock()`, `processVideoBlock()`, `processWebpageBlock()`, `processWebmapBlock()`, `processWebsceneBlock()`, and `processGalleryBlock()` to conditionally use detached methods
   - ✅ **Navigation Links:** Fixed duplicate navigation links in journal/series converter
   - ✅ **Element Processing and DOM Manipulation Fixed:** Fixed critical bugs in journal/series content processing
     - **Issue 1:** DIVs with classes like `image-container` were being caught by the generic DIV handler before class-specific checks
     - **Issue 2:** `removeSpanTags()` was causing DOM manipulation errors during HTML cleaning
     - **Error:** `HierarchyRequestError: Failed to execute 'insertBefore' on 'Node': Only one element on document allowed`
     - **Root Cause:** `removeSpanTags()` was manipulating a live NodeList while iterating, and using `doc.querySelectorAll('*')` which included document-level elements
     - **Fix 1:** Reordered if/else conditions in `processContentElement()` to check for elements with classes BEFORE checking for generic DIVs
     - **Fix 2:** Changed from `outerHTML` to `innerHTML` for P and DIV elements to avoid including outer wrapper tags
     - **Fix 3:** Fixed `removeSpanTags()` to:
       - Use `doc.body.querySelectorAll('*')` instead of `doc.querySelectorAll('*')` to stay within body
       - Convert NodeList to array before processing
       - Process elements in reverse order (innermost to outermost) to avoid parent-child manipulation conflicts
     - **Result:** All narrative content (text, images, embeds) is now properly extracted and added to sidecar panels without errors
   - ✅ **Image Caption Support:** Image captions and alt text are now properly extracted and included
     - Journal/Series: Extracts `caption` from media.image object and `alt` attribute from HTML img tags
     - Cascade: Already supported - extracts `caption` and `altText` from image block data
     - All captions and alt text are passed to the image nodes in the converted StoryMap
     - Empty strings are normalized to undefined to prevent empty caption/alt fields in output
     - Caption and alt text are properly set on `node.data.caption` and `node.data.alt` when non-empty
   - ✅ **Nested Container Handling:** Fixed processing of complex nested HTML structures
     - **Problem:** Classic stories often have nested `<div class="image-container">` elements that contain both text paragraphs and images
     - **Root Cause:** Converter was only extracting images from containers, ignoring text content within the same container
     - **Fix 1 - Content Processing:** Changed `image-container` and `caption` handling to recursively process all direct children instead of only looking for images
       - TypeScript (`journal-converter.ts`): Process all children via recursive `processContentElement()` calls
       - Python (`converter_json.py`): Process all children via recursive `_process_content_element()` calls
       - Python (`converter_v2.py`): Already handled paragraphs within containers, confirmed working
     - **Fix 2 - DOM Manipulation:** Updated `removeSpanTags` utility to wrap HTML fragments in a temporary container div to prevent document-level node manipulation errors
       - TypeScript (`utils.ts`): Wrap in `<div>`, query within wrapper, return wrapper.innerHTML
       - Python (`converter_json.py`, `converter_v2.py`): Wrap in `<div>`, unwrap within wrapper, return joined children
     - **Result:** All text content within nested containers is now properly extracted, even when mixed with images
     - **Note:** Fixes applied consistently across all three converter implementations (TypeScript web app, Python JSON converter, Python API converter)
   - Result: Clean, non-duplicated output in both journal/series and cascade converters with complete content extraction including captions and nested text
   - **Before Fix:**
     - Journal output: 493 lines with duplicate nodes in story root
     - Cascade output: 1435 lines (entire JSON duplicated + duplicate immersive text)
   - **After Fix:**
     - Journal output: Clean 493 lines, nodes only in sidecar slides with all narrative content
     - Cascade output: 697 lines (single clean structure, immersive content only in narrative panels)

10. **TypeScript Web App Implemented**

    - ✅ Complete client-side converter web app built with React/TypeScript/Vite
    - ✅ **Live Demo:** https://classic-storymap-converter.surge.sh/
    - ✅ Ported all Python conversion logic to TypeScript
    - ✅ Direct browser-to-ArcGIS REST API calls (no backend)
    - ✅ Manual token authentication (user copies `esri_aopc` from browser DevTools)
    - ✅ Token stored in session storage (cleared on tab close)
    - ✅ **Automatic image transfer** - downloads images from classic story resources, uploads to target story
    - ✅ Updates existing draft storymaps by replacing draft resource JSON
    - ✅ Minimal UI with clear status messages, error handling, and token help
    - ✅ Fixed schema mismatches to match Python output exactly:
      - Root structure: Added navigation node, changed cover type to "storycover", added config section
      - Node structure: Added config.size to all nodes (image, map, embed, gallery)
      - Narrative panels: Added position and size properties
      - Image/caption handling: Supports nested images (find_all for all img descendants)
      - **Image resources**: Proper structure based on source type:
        - Transferred AGO images: `{resourceId: "filename.jpg", provider: "item-resource", height, width}`
        - External URLs: `{src: "https://...", provider: "uri", height, width}`
    - Result: TypeScript output now byte-for-byte matches Python converter (except random IDs)
    - ✅ Module structure mirrors Python implementation:
      - `storymap-schema.ts` - Node/resource creators
      - `storymap-builder.ts` - JSON builder class
      - `journal-converter.ts` - Journal/Series converter
      - `cascade-converter.ts` - Cascade converter
      - `converter-factory.ts` - Converter selector
      - `utils.ts` - Shared utilities
      - `arcgis-client.ts` - REST API wrapper
      - `image-transfer.ts` - Image download/upload for preserving images
      - `auth.ts` - Token authentication
      - `Converter.tsx` - React UI component
    - Result: Fully functional browser-based converter with same conversion fidelity as Python

### Earlier Changes (October 16, 2025)

1. **Critical Bug Fixes**

   - ✅ **Series Type Detection:** Fixed `_detect_type()` to properly detect MapSeries vs MapJournal
   - ✅ **Empty Sidecars:** Now correctly processes sections from both `story.sections` (Journal) and `story.entries` (Series)
   - ✅ **Image Upload Timing:** Fixed resource upload ordering to ensure images available before item creation
   - Result: Series conversions now generate 25-31 nodes (was 7), narrative panels properly populated

2. **Embed Metadata Enhancement**

   - ✅ Added complete embed metadata structure per official schema
   - ✅ Fields now included: `embedSrc`, `allowSmallEmbeds`, `title`, `description`, `thumbnailUrl`, `providerUrl`
   - ✅ Updated all 5 embed creation locations to extract metadata from classic data
   - ✅ Auto-parses provider domain from URLs
   - Result: Embeds now have rich, schema-compliant metadata

3. **Comprehensive Documentation Created**

   - Detailed logic documentation with line-by-line explanations
   - Visual Mermaid flowcharts for all conversion paths
   - Improvement proposals with code examples

4. **JSON-to-JSON Converter Implemented**

   - Pure JSON transformation without API dependencies
   - Identical output structure to API version (validated against official schemas)
   - Modular architecture with StoryMapJSONBuilder
   - Separate converters for Journal/Series and Cascade
   - Factory pattern for automatic converter selection

5. **Schema Validation and Corrections**

   - Official ArcGIS StoryMaps JSON schemas integrated from `schemas/` directory
   - Corrected all node structures to match official schema (see "Schema Compliance" section for details)
   - Added comprehensive node validation against schema requirements
   - Added 16 detailed flowcharts including webmap, webscene, gallery, and embed processing

6. **Key Architecture Patterns Identified**

   - Deferred Settings Pattern: Collect settings during processing, apply post-save
   - Two-Phase Conversion: Structure creation → Property refinement
   - HTML Parsing Strategy: BeautifulSoup for content extraction and cleaning
   - Map Resource Configuration: Uses "minimal" type per consultation with Kuan
   - Video/Embed Resources: Always stored as URL references, never uploaded

7. **Critical Code Quality Issues Documented**
   - Duplicate code between converters
   - Deeply nested functions in Cascade converter
   - Multiple save/reload cycles impacting performance
   - Generic error handling making debugging difficult

## Schema Compliance

This project adheres to official ArcGIS StoryMaps JSON schemas. Key schema compliance notes:

### Property Name Corrections

All converters use `alt` (not `altText`) per official schema:

- **Images**: `node.data.alt` for alternative text
- **Embeds**: `node.data.alt` for embed descriptions
- **Galleries**: `node.data.alt` on individual image nodes

### Embed Structure

Embeds store URLs directly in node data (no resources):

```json
{
  "type": "embed",
  "config": { "size": "standard" },
  "data": {
    "url": "https://example.com/video",
    "display": "inline",
    "embedType": "video",
    "isEmbedSupported": true
  }
}
```

### Gallery Structure

Gallery children are image **node IDs** (not resource IDs):

```json
{
  "type": "gallery",
  "data": {
    "galleryLayout": "square-dynamic" // REQUIRED: square-dynamic, jigsaw, or filmstrip
  },
  "children": ["n-abc123", "n-def456"] // Image node IDs
}
```

### Map Nodes

Map nodes use type `webmap` with minimal resource configuration:

```json
{
  "type": "webmap",
  "config": {"size": "wide"},
  "data": {
    "map": "r-abc123",
    "extent": {...},
    "viewpoint": {...}
  }
}
```

Map resources use `type: "minimal"` with only `itemId` and `itemType` to avoid duplication between resource-level and node-level configurations (per consultation with Kuan).

### Conversion Logic Insights

1. **Sidecar Structure**

   ```
   sidecar (immersive)
   └── slide (immersive-slide)
       └── narrative (immersive-narrative-panel)
           └── content nodes (text, images, etc.)
   ```

2. **Node ID Generation**

   - Format: `n-{uuid.uuid4().hex[:6]}` (e.g., `n-a1b2c3`)
   - Resource IDs: `r-{uuid.uuid4().hex[:6]}`

3. **Map Processing**

   - Scale calculated from extent using coefficient 4.4 (Web Mercator approximation)
   - Layer visibility matched by ID or ID prefix
   - Viewpoint includes targetGeometry and scale
   - Resources set to "minimal" type to reduce payload

4. **Image Processing**

   - AGO resources downloaded locally with UUID filenames
   - Uploaded as StoryMap item resources
   - External URLs passed through as-is
   - Protocol-neutral URLs converted to https://

5. **HTML Content Processing**
   - BeautifulSoup parses classic HTML
   - Iterates through child elements
   - Extracts images, text, embeds
   - Cleans styling and non-essential tags
   - Creates appropriate StoryMap nodes

### Performance Characteristics

**API-Based Converter:**

- Journal with 10 sections: ~30-45 seconds
- Cascade with 5 immersive sections: ~45-60 seconds
- Bottleneck: Multiple API save/reload cycles for maps

**JSON-to-JSON Converter:**

- Same stories: ~5-10 seconds (no API calls)
- Bottleneck: Image downloads (if AGO resources present)
- Note: Excludes final upload time to create item

### Future Development Priorities

Based on IMPROVEMENTS.md analysis:

**Phase 1 (High Priority):**

- Fix critical bugs in converter_v2.py
- Extract utilities to shared module
- Add input validation

**Phase 2 (Medium Priority):**

- Create base converter class hierarchy
- Implement batch map processing
- Enhanced error handling with context

**Phase 3 (Low Priority):**

- Parallel image downloads
- Layer caching for repeated maps
- Transaction-based rollback mechanism

## Testing

Currently, testing is manual. Recommended test cases:

1. **Journal with maps**: Test map extent/layer preservation
2. **Journal with images**: Test AGO image download
3. **Series with embeds**: Test video/webpage conversion
4. **Cascade with cover**: Test theme detection
5. **Cascade with immersive**: Test floating sidecar creation
6. **Mixed content**: Test all media types in one story

Compare output between API and JSON converters for consistency.

## Contributing

When making changes:

1. Update this README with discoveries and changes
2. Document logic in CONVERTER_LOGIC.md if modifying conversion process
3. Update IMPROVEMENTS.md if identifying new issues or solutions
4. Maintain backward compatibility with existing conversions

## Environment Notes

- **Operating System**: Windows 10+
- **Python Version**: 3.11 (required by project configuration)
- **Shell**: PowerShell (preferred, per user preference)
- **Authentication**: Uses environment variables or ArcGIS "home" authentication

## License

[Add license information here]

## Support

For issues or questions:

1. Check CONVERTER_LOGIC.md for detailed behavior documentation
2. Review CONVERTER_LOGIC_DIAGRAM.md for visual process flow
3. Consult IMPROVEMENTS.md for known issues and workarounds

---

**Note**: This is a development tool for migrating classic stories. Always review converted stories before publishing to ensure content accuracy and completeness.
