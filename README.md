

# Classic StoryMap to ArcGIS StoryMaps Converter

Convert Classic ArcGIS StoryMaps (MapJournal, MapSeries, Cascade) to the new ArcGIS StoryMaps format.

## How to Use

**API-Based Conversion:**
Edit config in `converter_v2.py` and run:
```powershell
python converter_v2.py
```

**JSON-to-JSON Conversion:**
Import and use `convert_classic_to_json` and `save_json_to_file` in Python.

**Testing:**
```powershell
python test_converter.py
```

**Web App:**
```powershell
cd converter-app
npm install
npm run dev
```
Open `http://localhost:5173` and follow the UI instructions.

## Requirements

- Python 3.11
- arcgis >= 2.1.0.2 (for API-based conversion)
- beautifulsoup4
- python-dotenv (optional)

## License

[Add license information here]


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

### davi6569/fix-npm-run-dev
Found that /converter-app/index.html contained hardcoded references to the ./assets folder which is only
created after a production build. Edited those lines to point to /src/main.tsx so Vite can run successfully
### davi6569/AGO-oath2-integration
To ease user workflow, added a button to do authentication via ArcGIS Online OAuth2. Removed the token input field and its references from index.html and Converter.tsx also updated .gitignore to exclude the node_modules folder
### davi6569/minimal-test
- Changed "Open Converted Story" to "Click to Finish Publishing" and modified the url to point to the story builder instead of the story viewer. This process won't work for integration into AGSM, but want to get it working for testing. 
- Added folders to test_data/classics to ease identification of json files for testing.
- Hard coded test json file in Converter.tsx

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
