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

# Classic StoryMap to ArcGIS StoryMaps Converter

A comprehensive tool for converting Classic ArcGIS StoryMaps (MapJournal, MapSeries, Cascade) to the new ArcGIS StoryMaps format.

## Overview

This project provides three approaches for converting classic stories:

- **API-Based Conversion** (`converter_v2.py`): Uses the ArcGIS Python API to create StoryMaps
- **JSON-to-JSON Conversion** (`converter_json.py`): Direct JSON transformation without API calls
- **Client-Side Web App** (`converter-app/`): TypeScript/React app that converts stories directly in the browser

## Project Structure

See the folder tree for details on Python scripts, web app, schemas, and test data.

## Supported Classic StoryMap Types

- **MapJournal**: Side panel navigation
- **MapSeries**: Tab-based navigation
- **Cascade**: Scrolling narrative

All types convert to ArcGIS StoryMaps with sidecar layouts.

## Requirements

- Python 3.11
- arcgis >= 2.1.0.2 (for API-based conversion)
- beautifulsoup4
- python-dotenv (optional, for .env file support)

## Installation

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file for ArcGIS credentials (see example in repo).

## Usage

### API-Based Conversion

Edit config variables in `converter_v2.py`, then run:

```powershell
python converter_v2.py
```

### JSON-to-JSON Conversion

Import and use `convert_classic_to_json` and `save_json_to_file` in your Python code.

### Testing

Run batch conversions and validation:

```powershell
python test_converter.py
```

### Client-Side Web App

```powershell
cd converter-app
npm install
npm run dev
```

Open `http://localhost:5173` in your browser. Sign in to ArcGIS Online, copy your token from the 'traffic' network request in DevTools, and follow the UI instructions.

## Key Features

- No backend required for web app
- Direct REST API calls to ArcGIS Online
- Automatic image transfer
- Schema-compliant output

## License

[Add license information here]

## Support

For issues or questions, see CONVERTER_LOGIC.md and IMPROVEMENTS.md.

---

**Note**: This is a development tool for migrating classic stories. Always review converted stories before publishing to ensure content accuracy and completeness.
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
