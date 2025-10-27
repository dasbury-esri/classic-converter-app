# TypeScript Converter Flow Diagrams

Visual documentation for the TypeScript-based Classic StoryMap converter web application. These diagrams complement the Python converter diagrams in the root `CONVERTER_LOGIC_DIAGRAM.md`.

---

## 1. High-Level TypeScript Conversion Flow

```mermaid
flowchart TD
    Start([User initiates conversion]) --> LoadJSON[Load Classic Story JSON]
    LoadJSON --> Factory[convertClassicToJson<br/>converter-factory.ts]
    Factory --> GetConverter[ConverterFactory.getConverter]

    GetConverter --> CheckValues{values<br/>exists?}
    CheckValues -->|No| Error1[Throw Error:<br/>Invalid JSON]
    CheckValues -->|Yes| CheckStory{values.story<br/>exists?}

    CheckStory -->|Yes| CheckSections{sections or<br/>entries exist?}
    CheckSections -->|Yes| CreateJournal[new JournalSeriesConverter]
    CheckSections -->|No| CheckCascade

    CheckStory -->|No| CheckCascade{values.sections<br/>exists?}
    CheckCascade -->|Yes| CreateCascade[new CascadeConverter]
    CheckCascade -->|No| Error2[Throw Error:<br/>Unknown type]

    CreateJournal --> Convert[converter.convert]
    CreateCascade --> Convert

    Convert --> Return[Return StoryMap JSON]
    Return --> End([Complete])

    style Factory fill:#e1f5ff
    style CreateJournal fill:#d4edda
    style CreateCascade fill:#d4edda
    style Convert fill:#fff3cd
```

---

## 2. StoryMapJSONBuilder Overview

```mermaid
flowchart TD
    Start([Create Builder]) --> Init[new StoryMapJSONBuilder<br/>themeId]
    Init --> CreateBase[createBaseStorymapJson]

    CreateBase --> Methods{Builder Methods}

    Methods --> AddNode[addNode<br/>Add to story root]
    Methods --> Detached[createDetachedNode<br/>Not added to root]

    Methods --> Text[addText / addTextDetached]
    Methods --> Image[addImage / addImageDetached]
    Methods --> Map[addMap / addMapDetached]
    Methods --> Embed[addEmbed / addEmbedDetached]
    Methods --> Gallery[addGallery / addGalleryDetached]

    Methods --> Sidecar[addSidecar<br/>Creates immersive structure]
    Sidecar --> Slide[Returns sidecarId,<br/>slideId, narrativeId]

    Methods --> AddSlide[addSlideToSidecar<br/>media + narrative content]

    Methods --> Resources[addResource<br/>Create resource]

    Methods --> SetCover[setCover<br/>Set title]
    Methods --> SetTheme[setTheme<br/>Apply theme]

    Methods --> GetJSON[getJson<br/>Return final JSON]

    style CreateBase fill:#e1f5ff
    style Detached fill:#fff3cd
    style Sidecar fill:#d4edda
```

---

## 3. Journal/Series Converter Flow

```mermaid
flowchart TD
    Start([JournalSeriesConverter.convert]) --> GetTitle[Get title from values]
    GetTitle --> CreateSidecar[builder.addSidecar<br/>'docked-panel']

    CreateSidecar --> DetectType{Detect type:<br/>journal or series?}
    DetectType -->|story.sections| UseJournal[Use sections array]
    DetectType -->|story.entries| UseSeries[Use entries array]

    UseJournal --> LoopSections[Loop through sections]
    UseSeries --> LoopSections

    LoopSections --> ProcessSection[processSection<br/>for each section]

    ProcessSection --> ProcessMedia[processSectionMedia]
    ProcessMedia --> MediaType{media.type?}
    MediaType -->|webmap| WebmapMedia[processWebmapMedia]
    MediaType -->|image| ImageMedia[processImageMedia]
    MediaType -->|video/webpage| EmbedMedia[processEmbedMedia]

    WebmapMedia --> MediaReturn[Return mediaNodeId]
    ImageMedia --> MediaReturn
    EmbedMedia --> MediaReturn

    ProcessSection --> ProcessNarrative[processNarrativeContent]

    ProcessNarrative --> ParseTitle[Parse title with parseHtmlText]
    ParseTitle --> AddTitle[builder.addTextDetached<br/>h2 heading]

    ProcessNarrative --> ParseContent[Parse content HTML<br/>DOMParser]
    ParseContent --> LoopElements[Loop through elements]
    LoopElements --> ProcessElement[processContentElement]

    ProcessElement --> ReturnNarrative[Return narrativeContentIds]
    MediaReturn --> AddSlide[builder.addSlideToSidecar<br/>mediaNodeId + narrativeIds]
    ReturnNarrative --> AddSlide

    AddSlide --> MoreSections{More<br/>sections?}
    MoreSections -->|Yes| LoopSections
    MoreSections -->|No| RemoveEmpty[Remove initial empty slide]

    RemoveEmpty --> SetCover[builder.setCover]
    SetCover --> SetTheme[builder.setTheme]
    SetTheme --> Return[Return storymap JSON]
    Return --> End([Complete])

    style CreateSidecar fill:#d4edda
    style ProcessMedia fill:#e1f5ff
    style ProcessNarrative fill:#fff3cd
    style AddSlide fill:#d4edda
```

---

## 4. Journal/Series Content Processing

```mermaid
flowchart TD
    Start([processContentElement]) --> CheckTag{element.tagName}

    CheckTag -->|IMG| ExtractImg[Extract src, alt<br/>builder.addImageDetached]

    CheckTag -->|P| CheckImgInP{Contains<br/>img tags?}
    CheckImgInP -->|Yes| ExtractPImg[Extract each img<br/>addImageDetached]
    CheckImgInP -->|No/Also| GetPText[Get element.innerHTML]
    GetPText --> CleanP[removeSpanTags]
    CleanP --> CheckEmpty{isNonEmptyString?}
    CheckEmpty -->|Yes| AddPText[builder.addTextDetached<br/>paragraph]
    CheckEmpty -->|No| Skip1[Skip]

    CheckTag -->|DIV with class| CheckClass{Class type?}
    CheckClass -->|image-container<br/>or caption| ProcessChildren[Process all<br/>direct children<br/>recursively]
    CheckClass -->|iframe-container| ExtractIframe[Extract iframe src<br/>addEmbedDetached]
    CheckClass -->|pullquote| GetDivText[Get innerHTML]
    GetDivText --> CleanDiv[removeSpanTags]
    CleanDiv --> CheckDivEmpty{isNonEmptyString?}
    CheckDivEmpty -->|Yes| AddDivText[builder.addTextDetached]
    CheckDivEmpty -->|No| Skip2[Skip]

    CheckTag -->|DIV no class| GenericDiv[Get innerHTML<br/>removeSpanTags<br/>addTextDetached]

    ExtractImg --> ReturnIds[Return nodeIds array]
    AddPText --> ReturnIds
    ProcessChildren --> ReturnIds
    ExtractIframe --> ReturnIds
    AddDivText --> ReturnIds
    GenericDiv --> ReturnIds
    Skip1 --> ReturnIds
    Skip2 --> ReturnIds

    style ProcessChildren fill:#fff3cd
    style CleanP fill:#e1f5ff
    style CleanDiv fill:#e1f5ff
```

---

## 5. Cascade Converter Flow

```mermaid
flowchart TD
    Start([CascadeConverter.convert]) --> GetTitle[Get title from values]
    GetTitle --> LoopSections[Loop through<br/>values.sections]

    LoopSections --> DetectSection{section.type?}

    DetectSection -->|cover| ProcessCover[processCover<br/>Sets builder.setCover]
    DetectSection -->|sequence| ProcessSequence[processSequence<br/>Adds content nodes]
    DetectSection -->|immersive| ProcessImmersive[processImmersive<br/>Creates sidecar]
    DetectSection -->|title| ProcessTitle[processTitle<br/>Adds separator + text]
    DetectSection -->|credits| Skip[Skip - handled by base]

    ProcessSequence --> LoopBlocks[Loop through<br/>section.blocks]
    LoopBlocks --> ProcessBlock[processBlock<br/>returnIdOnly=false]

    ProcessImmersive --> CreateSidecar[builder.addSidecar<br/>'floating-panel']
    CreateSidecar --> LoopViews[Loop through<br/>section.views]
    LoopViews --> GetBackground[processImmersiveBackground<br/>returnIdOnly=true]
    LoopViews --> GetPanel[processImmersivePanel<br/>returnIdOnly=true]
    GetBackground --> AddImmSlide[builder.addSlideToSidecar<br/>backgroundId + panelIds]
    GetPanel --> AddImmSlide

    ProcessBlock --> BlockType{block.type?}
    BlockType -->|text| TextBlock[processTextBlock]
    BlockType -->|image| ImageBlock[processImageBlock]
    BlockType -->|video| VideoBlock[processVideoBlock]
    BlockType -->|webpage| WebpageBlock[processWebpageBlock]
    BlockType -->|webmap| WebmapBlock[processWebmapBlock]
    BlockType -->|webscene| WebsceneBlock[processWebsceneBlock]
    BlockType -->|gallery| GalleryBlock[processGalleryBlock]

    TextBlock --> CheckReturn{returnIdOnly?}
    ImageBlock --> CheckReturn
    VideoBlock --> CheckReturn
    WebpageBlock --> CheckReturn
    WebmapBlock --> CheckReturn
    WebsceneBlock --> CheckReturn
    GalleryBlock --> CheckReturn

    CheckReturn -->|true| UseDetached[Use addXXXDetached<br/>Return nodeId only]
    CheckReturn -->|false| UseNormal[Use addXXX<br/>Add to story root]

    ProcessCover --> MoreSections{More<br/>sections?}
    ProcessSequence --> MoreSections
    AddImmSlide --> MoreSections
    ProcessTitle --> MoreSections
    Skip --> MoreSections
    UseDetached --> MoreSections
    UseNormal --> MoreSections

    MoreSections -->|Yes| LoopSections
    MoreSections -->|No| SetTheme[builder.setTheme]
    SetTheme --> Return[Return storymap JSON]
    Return --> End([Complete])

    style ProcessImmersive fill:#d4edda
    style CreateSidecar fill:#d4edda
    style CheckReturn fill:#fff3cd
```

---

## 6. Cascade Block Processing

```mermaid
flowchart TD
    Start([processBlock]) --> CheckReturn{returnIdOnly<br/>parameter?}

    CheckReturn -->|true| DetachedMode[Detached Mode<br/>For sidecar content]
    CheckReturn -->|false| NormalMode[Normal Mode<br/>Add to story root]

    DetachedMode --> BlockType{block.type?}
    NormalMode --> BlockType

    BlockType -->|text| TextDetached{returnIdOnly?}
    TextDetached -->|true| AddTextD[builder.addTextDetached<br/>Returns nodeId]
    TextDetached -->|false| AddText[builder.addText<br/>Adds to story]

    BlockType -->|image| ImageDetached{returnIdOnly?}
    ImageDetached -->|true| AddImageD[builder.addImageDetached<br/>caption, alt from block]
    ImageDetached -->|false| AddImage[builder.addImage<br/>caption, alt from block]

    BlockType -->|video| VideoDetached{returnIdOnly?}
    VideoDetached -->|true| AddEmbedD1[builder.addEmbedDetached<br/>embedType: 'video']
    VideoDetached -->|false| AddEmbed1[builder.addEmbed<br/>embedType: 'video']

    BlockType -->|webpage| WebpageDetached{returnIdOnly?}
    WebpageDetached -->|true| AddEmbedD2[builder.addEmbedDetached<br/>embedType: 'link']
    WebpageDetached -->|false| AddEmbed2[builder.addEmbed<br/>embedType: 'link']

    BlockType -->|webmap| MapDetached{returnIdOnly?}
    MapDetached -->|true| CreateMapD[createDetachedMapNode<br/>extent, viewpoint, layers]
    MapDetached -->|false| CreateMap[createMapNode<br/>extent, viewpoint, layers]

    BlockType -->|gallery| GalleryDetached{returnIdOnly?}
    GalleryDetached -->|true| AddGalleryD[builder.addGalleryDetached<br/>Process images as detached]
    GalleryDetached -->|false| AddGallery[builder.addGallery<br/>Process images normally]

    AddTextD --> ReturnId[Return nodeId]
    AddImageD --> ReturnId
    AddEmbedD1 --> ReturnId
    AddEmbedD2 --> ReturnId
    CreateMapD --> ReturnId
    AddGalleryD --> ReturnId

    AddText --> ReturnId
    AddImage --> ReturnId
    AddEmbed1 --> ReturnId
    AddEmbed2 --> ReturnId
    CreateMap --> ReturnId
    AddGallery --> ReturnId

    style DetachedMode fill:#fff3cd
    style NormalMode fill:#e1f5ff
```

---

## 7. Utility Functions

```mermaid
flowchart TD
    Start([Utility Functions<br/>utils.ts]) --> Functions{Function Type}

    Functions --> RemoveSpan[removeSpanTags]
    RemoveSpan --> WrapDiv[Wrap HTML in<br/>temporary div container]
    WrapDiv --> ParseHTML[DOMParser.parseFromString<br/>text/html]
    ParseHTML --> GetWrapper[Get wrapper div<br/>from doc.body]
    GetWrapper --> QueryAll[wrapper.querySelectorAll<br/>Get all tags]
    QueryAll --> ArrayConvert[Convert NodeList<br/>to Array]
    ArrayConvert --> ReverseLoop[Process in reverse<br/>innermost to outermost]
    ReverseLoop --> CheckAccepted{Tag in accepted<br/>list?}
    CheckAccepted -->|No| Unwrap[parent.insertBefore<br/>parent.removeChild]
    CheckAccepted -->|Yes| Keep[Keep tag]
    Unwrap --> MoreTags{More tags?}
    Keep --> MoreTags
    MoreTags -->|Yes| ReverseLoop
    MoreTags -->|No| ReturnInner[Return wrapper.innerHTML<br/>Unwraps temp div]

    Functions --> ParseText[parseHtmlText]
    ParseText --> CallRemove[Call removeSpanTags]
    CallRemove --> CreateDOM[DOMParser for text/html]
    CreateDOM --> GetText[doc.body.textContent<br/>Extract plain text]
    GetText --> ReturnText[Return cleaned text]

    Functions --> EnsureHTTPS[ensureHttpsProtocol]
    EnsureHTTPS --> CheckProtocol{Has protocol?}
    CheckProtocol -->|No| AddHTTPS[Prepend https://]
    CheckProtocol -->|http://| ReplaceHTTPS[Replace with https://]
    CheckProtocol -->|https://| ReturnURL[Return as-is]
    AddHTTPS --> ReturnURL
    ReplaceHTTPS --> ReturnURL

    Functions --> ExtractProvider[extractProviderUrl]
    ExtractProvider --> ParseURL[new URL<br/>Parse URL string]
    ParseURL --> GetOrigin[Return url.origin<br/>protocol + hostname + port]

    Functions --> CalcScale[determineScaleZoomLevel]
    CalcScale --> CheckExtent{extent valid?}
    CheckExtent -->|No| ReturnNull[Return null, null]
    CheckExtent -->|Yes| CalcHeight[height = ymax - ymin]
    CalcHeight --> CalcWidth[width = xmax - xmin]
    CalcWidth --> UseMax[Use max of height/width]
    UseMax --> ApplyCoeff[Apply coefficient 4.4<br/>Web Mercator approx]
    ApplyCoeff --> FindScale[Find closest Scales value]
    FindScale --> CalcZoom[Calculate zoom level<br/>Based on scale]
    CalcZoom --> ReturnBoth[Return scale, zoom]

    style WrapDiv fill:#fff3cd
    style ReverseLoop fill:#e1f5ff
    style ApplyCoeff fill:#d4edda
```

---

## Key Differences from Python Implementation

### 1. Detached Node Pattern

TypeScript implementation uses explicit "detached" methods for sidecar content:

- `addTextDetached()`, `addImageDetached()`, etc.
- Prevents duplicate nodes in story root
- Cleaner separation of concerns

### 2. DOM Manipulation

TypeScript uses browser's native `DOMParser`:

- `DOMParser.parseFromString()` instead of BeautifulSoup
- `querySelectorAll()` for element selection
- Must wrap HTML in temporary container div to prevent document-level manipulation errors

### 3. Type Safety

TypeScript provides compile-time type checking:

- Interface definitions in `storymap.d.ts`
- Type-safe function parameters
- Catches errors before runtime

### 4. Async Operations

TypeScript version handles async image transfers:

- Downloads images from classic story resources
- Uploads to target story via REST API
- Updates JSON with new resource IDs

### 5. Factory Pattern

Explicit factory class for converter selection:

- `ConverterFactory.getConverter()`
- Cleaner entry point
- Better error handling for unknown types

---

## Notes

- All line numbers reference the TypeScript source files in `converter-app/src/converter/`
- Diagrams focus on core conversion logic (not REST API calls or UI)
- See main project `CONVERTER_LOGIC_DIAGRAM.md` for Python converter diagrams
- Both implementations produce identical JSON output (except for random IDs)
