/**
 * TypeScript interfaces for ArcGIS StoryMap JSON structures
 * Based on official ArcGIS StoryMaps schema
 */

export interface StoryMapJSON {
  type: 'storymap';
  version: string;
  root: string;
  nodes: Record<string, StoryMapNode>;
  resources: Record<string, StoryMapResource>;
}

export interface StoryMapNode {
  type: string;
  data?: Record<string, any>;
  config?: Record<string, any>;
  children?: string[];
}

export interface StoryMapResource {
  type: string;
  data: Record<string, any>;
}

// Specific node types
export interface TextNode extends StoryMapNode {
  type: 'text';
  data: {
    type: 'h2' | 'h3' | 'h4' | 'paragraph' | 'quote';
    text: string;
    textAlignment?: 'start' | 'center' | 'end';
  };
}

export interface ImageNode extends StoryMapNode {
  type: 'image';
  data: {
    image: string; // resource ID
    alt?: string;
    caption?: string;
  };
  config: {
    size: 'small' | 'medium' | 'large' | 'full-width' | 'float';
    display?: 'standard' | 'float' | 'wide';
    floatAlignment?: 'start' | 'center' | 'end';
  };
}

export interface MapNode extends StoryMapNode {
  type: 'webmap';
  data: {
    map: string; // resource ID
    extent?: Extent;
    viewpoint?: Viewpoint;
    zoom?: number;
    mapLayers?: MapLayer[];
    caption?: string;
    alt?: string;
  };
}

export interface EmbedNode extends StoryMapNode {
  type: 'embed';
  data: {
    url: string;
    embedType: 'video' | 'link' | 'rich';
    display?: 'card' | 'inline';
    isEmbedSupported?: boolean;
    allowSmallEmbeds?: boolean;
    embedSrc?: string;
    caption?: string;
    alt?: string;
    title?: string;
    description?: string;
    thumbnailUrl?: string;
    providerUrl?: string;
  };
}

export interface GalleryNode extends StoryMapNode {
  type: 'gallery';
  data: {
    caption?: string;
    alt?: string;
  };
  config: {
    galleryLayout: 'square-dynamic' | 'horizontal-scroll' | 'grid';
  };
  children: string[]; // image node IDs
}

export interface SidecarNode extends StoryMapNode {
  type: 'immersive';
  data: {
    type: 'sidecar';
    subtype: 'docked-panel' | 'floating-panel';
  };
  children: string[]; // slide IDs
}

export interface SlideNode extends StoryMapNode {
  type: 'immersive-slide';
  data: {
    transition?: 'fade' | 'slide';
  };
  children: string[]; // [narrative panel ID, media node ID]
}

export interface NarrativePanelNode extends StoryMapNode {
  type: 'immersive-narrative-panel';
  data: {
    panelStyle?: 'themed' | 'custom';
  };
  children: string[]; // content node IDs
}

// Resources
export interface ImageResource extends StoryMapResource {
  type: 'image';
  data: {
    type: 'image';
    resourceId?: string;
    path?: string;
    url?: string;
  };
}

export interface MapResource extends StoryMapResource {
  type: 'webmap';
  data: {
    type: 'minimal';
    itemId: string;
    itemType: 'Web Map' | 'Web Scene';
  };
}

export interface ThemeResource extends StoryMapResource {
  type: 'story-theme';
  data: {
    themeId?: string;
    themeItemId?: string;
  };
}

// Supporting types
export interface Extent {
  xmin: number;
  ymin: number;
  xmax: number;
  ymax: number;
  spatialReference?: {
    wkid: number;
  };
}

export interface Viewpoint {
  targetGeometry: Extent;
  scale: number;
}

export interface MapLayer {
  id: string;
  title?: string;
  visible: boolean;
}

// Classic StoryMap types
export interface ClassicStoryMapJSON {
  values: {
    title?: string;
    story?: {
      sections?: ClassicSection[];
      entries?: ClassicSection[];
    };
    sections?: ClassicSection[];
    settings?: {
      theme?: {
        colors?: {
          themeMajor?: string;
        };
      };
    };
  };
}

export interface ClassicSection {
  title?: string;
  content?: string;
  description?: string;
  media?: {
    type: string;
    webmap?: ClassicWebMap;
    image?: ClassicMedia;
    video?: ClassicMedia;
    webpage?: ClassicMedia;
  };
  foreground?: any;
  background?: any;
  views?: any[];
  type?: string;
}

export interface ClassicWebMap {
  id: string;
  extent?: Extent;
  layers?: ClassicLayer[];
}

export interface ClassicLayer {
  id: string;
  title?: string;
  visibility: boolean;
}

export interface ClassicMedia {
  url: string;
  altText?: string;
  caption?: string;
  title?: string;
  description?: string;
  frameTag?: string;
}

