/* eslint-disable @typescript-eslint/no-explicit-any */


/**
 * Journal/Series JSON Converter
 * Converts MapJournal and MapSeries to StoryMap JSON
 * Ported from JournalSeriesJSONConverter class in converter_json.py
 */

import type { ClassicStoryMapJSON, ClassicSection } from '../types/storymap';
import { StoryMapJSONBuilder } from './storymap-builder';
import {
  determineScaleZoomLevel,
  ensureHttpsProtocol,
  parseHtmlText,
  removeSpanTags,
  isNonEmptyString,
  extractProviderUrl
} from './utils';
import { EMBEDLY_TYPES } from './storymap-schema';

export class MapJournalConverter {
  private classicJson: ClassicStoryMapJSON;
  private themeId: string;
  private builder: StoryMapJSONBuilder;
  private classicType: 'journal' | 'series';

  constructor(classicJson: ClassicStoryMapJSON, themeId: string = 'summit') {
    this.classicJson = classicJson;
    this.themeId = themeId;
    this.builder = new StoryMapJSONBuilder(themeId);
    this.classicType = this.detectType();
  }

  /**
   * Detect if this is a Journal or Series
   */
  private detectType(): 'journal' | 'series' {
    const story = this.classicJson.values?.story;
    if (story?.sections) {
      return 'journal';
    } else if (story?.entries) {
      return 'series';
    }
    return 'journal'; // default
  }

  /**
   * Main conversion method
   */
  convert(): any {
    // Get title
    const coverTitle = this.classicJson.values?.title || 'Untitled Story';

    // Create sidecar
    const { sidecarId, slideId: initialSlideId, narrativeId: initialNarrativeId } =
      this.builder.addSidecar('docked-panel');

    // Get sections
    const sections =
      this.classicType === 'journal'
        ? this.classicJson.values?.story?.sections || []
        : this.classicJson.values?.story?.entries || [];

    const hasSections = sections.length > 0;

    // Process each section as a slide
    for (const section of sections) {
      this.processSection(section, sidecarId);
    }

    // Remove initial empty slide if we added real slides
    if (hasSections) {
      const storymap = this.builder.getJson();
      const sidecarNode = storymap.nodes[sidecarId];
      if (sidecarNode.children) {
        const index = sidecarNode.children.indexOf(initialSlideId);
        if (index !== -1) {
          sidecarNode.children.splice(index, 1);
        }
      }
      delete storymap.nodes[initialSlideId];
      delete storymap.nodes[initialNarrativeId];
    }

    // Set cover
    this.builder.setCover(`${coverTitle}`);

    // Set theme
    this.builder.setTheme(this.themeId);

    return this.builder.getJson();
  }

  /**
   * Process a single section as a sidecar slide
   */
  private processSection(section: ClassicSection, sidecarId: string): void {
    // Get media
    const mediaNodeId = this.processSectionMedia(section);

    // Get narrative content
    const narrativeContentIds = this.processNarrativeContent(section);

    // Add slide to sidecar
    this.builder.addSlideToSidecar(sidecarId, mediaNodeId, narrativeContentIds);
  }

  /**
   * Process section media (map, image, video, webpage)
   */
  private processSectionMedia(section: ClassicSection): string | undefined {
    const media = section.media;
    if (!media) return undefined;

    const mediaType = media.type;

    if (mediaType === 'webmap') {
      return this.processWebmapMedia(media);
    } else if (mediaType === 'image') {
      return this.processImageMedia(media);
    } else if (mediaType === 'video' || mediaType === 'webpage') {
      return this.processEmbedMedia(media, mediaType);
    }

    return undefined;
  }

  /**
   * Process webmap media
   */
  private processWebmapMedia(media: any): string | undefined {
    const webmapData = media.webmap;
    if (!webmapData) return undefined;

    const mapId = webmapData.id;
    const extent = webmapData.extent;
    const layers = webmapData.layers || [];

    // Calculate viewpoint
    let viewpoint;
    let zoom;
    if (extent) {
      const result = determineScaleZoomLevel(extent);
      if (result) {
        viewpoint = {
          targetGeometry: extent,
          scale: result.scale
        };
        zoom = result.zoom;
      }
    }

    // Build layer visibility
    let mapLayers;
    if (layers.length > 0) {
      mapLayers = layers.map((layer: any) => ({
        id: layer.id,
        visible: layer.visibility !== undefined ? layer.visibility : true
      }));
    }

    // Add map as detached node for sidecar (don't add to story root)
    const { nodeId } = this.builder.addMapDetached(
      mapId,
      extent,
      viewpoint,
      zoom,
      mapLayers,
      'Web Map'
    );

    return nodeId;
  }

  /**
   * Process image media
   */
  private processImageMedia(media: any): string | undefined {
    const imageData = media.image;
    if (!imageData) return undefined;

    const url = imageData.url || '';
    const alt = imageData.altText || undefined;
    const caption = imageData.caption || undefined;

    // In browser, we can't download cross-origin images, so just pass URL
    // Add as detached node for sidecar (don't add to story root)
    const nodeId = this.builder.addImageDetached(url, caption, alt);

    return nodeId;
  }

  /**
   * Process video/webpage embed media
   */
  private processEmbedMedia(media: any, mediaType: string): string | undefined {
    const embedData = media[mediaType];
    if (!embedData) return undefined;

    let url = embedData.url || '';

    // Get iframe URL if available
    if (embedData.frameTag) {
      const parser = new DOMParser();
      const doc = parser.parseFromString(embedData.frameTag, 'text/html');
      const iframe = doc.querySelector('iframe');
      if (iframe?.src) {
        url = iframe.src;
      }
    }

    // Ensure https
    url = ensureHttpsProtocol(url.trim().replace(/\/$/, ''));

    // Determine embed type
    const embedlyType = EMBEDLY_TYPES[mediaType] || 'link';

    // Extract metadata
    const alt = embedData.altText;
    const title = embedData.title;
    const description = embedData.description;
    const caption = embedData.caption;
    const providerUrl = extractProviderUrl(url);

    // Add embed as detached node for sidecar (don't add to story root)
    const nodeId = this.builder.addEmbedDetached(
      url,
      embedlyType,
      'inline',
      caption,
      alt,
      title,
      description,
      undefined,
      providerUrl
    );

    return nodeId;
  }

  /**
   * Process narrative content for a section
   */
  private processNarrativeContent(section: ClassicSection): string[] {
    const contentIds: string[] = [];

    // Add title
    const title = section.title || '';
    if (title) {
      const titleText = parseHtmlText(title);
      if (titleText.trim()) {
        // Use detached node for sidecar narrative content
        const titleId = this.builder.addTextDetached(titleText, 'h2', 'start');
        contentIds.push(titleId);
      }
    }

    // Get content
    const content =
      this.classicType === 'journal'
        ? section.content || ''
        : section.description || '';

    if (!content) {
      return contentIds;
    }

    // Parse HTML content
    const parser = new DOMParser();
    const doc = parser.parseFromString(content, 'text/html');

    for (const element of Array.from(doc.body.children)) {
      try {
        const nodeIds = this.processContentElement(element);
        contentIds.push(...nodeIds);
      } catch (ex) {
        console.error('Error processing content element:', ex);
      }
    }

    return contentIds;
  }

  /**
   * Process a single content element
   */
  private processContentElement(element: Element): string[] {
    const nodeIds: string[] = [];

    // Handle images
    if (element.tagName === 'IMG') {
      const url = element.getAttribute('src') || '';
      const alt = element.getAttribute('alt') || undefined;
      // Use detached node for sidecar narrative content
      const nodeId = this.builder.addImageDetached(url, undefined, alt, 'wide');
      nodeIds.push(nodeId);
    }
    // Handle paragraphs
    else if (element.tagName === 'P') {
      // Check for images in paragraph
      const images = element.querySelectorAll('img');
      images.forEach((img) => {
        const url = img.getAttribute('src') || '';
        const alt = img.getAttribute('alt') || undefined;
        // Use detached node for sidecar narrative content
        const nodeId = this.builder.addImageDetached(url, undefined, alt, 'wide');
        nodeIds.push(nodeId);
      });

      // Get text content (use innerHTML to avoid the outer <p> tag)
      const text = element.innerHTML;
      if (text && text.length > 0) {
        const cleanedText = removeSpanTags(text);
        if (isNonEmptyString(cleanedText)) {
          // Use detached node for sidecar narrative content
          const nodeId = this.builder.addTextDetached(cleanedText, 'paragraph', 'start');
          nodeIds.push(nodeId);
        }
      }
    }
    // Handle elements with classes (check this BEFORE generic divs)
    else if (element.classList.length > 0) {
      if (
        element.classList.contains('caption') ||
        element.classList.contains('image-container')
      ) {
        // Process all direct children of the container
        // This handles cases where the container has both text and images
        const children = Array.from(element.children);
        for (const child of children) {
          const childNodeIds = this.processContentElement(child);
          nodeIds.push(...childNodeIds);
        }
      } else if (element.classList.contains('iframe-container')) {
        const iframe = element.querySelector('iframe');
        if (iframe) {
          let url = (iframe.getAttribute('src') || '').trim().replace(/\/$/, '');
          url = ensureHttpsProtocol(url);

          // Determine type
          const embedlyType = element.classList.contains('mj-video-by-url')
            ? 'video'
            : 'link';
          const display = element.classList.contains('mj-video-by-url')
            ? 'inline'
            : 'card';

          const title = iframe.getAttribute('title') || undefined;
          const providerUrl = extractProviderUrl(url);

          // Use detached node for sidecar narrative content
          const nodeId = this.builder.addEmbedDetached(
            url,
            embedlyType,
            display,
            undefined,
            undefined,
            title,
            undefined,
            undefined,
            providerUrl
          );
          nodeIds.push(nodeId);
        }
      }
    }
    // Handle generic divs (after checking for specific classes)
    else if (element.tagName === 'DIV') {
      const text = element.innerHTML;
      const cleanedText = removeSpanTags(text);
      if (isNonEmptyString(cleanedText)) {
        // Use detached node for sidecar narrative content
        const nodeId = this.builder.addTextDetached(cleanedText, 'paragraph', 'start');
        nodeIds.push(nodeId);
      }
    }

    return nodeIds;
  }

  /**
   * Get list of local images for cleanup
   */
  getLocalImages(): string[] {
    return this.builder.getLocalImages();
  }
}

