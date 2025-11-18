/* eslint-disable @typescript-eslint/no-explicit-any */

/**
 * Journal JSON Converter
 * Converts Map Journal to StoryMap JSON
 * Ported from JournalSeriesJSONConverter class in converter_json.py
 */

import type { ClassicStoryMapJSON, ClassicSection } from '../types/storymap';
import { StoryMapJSONBuilder } from './storymap-builder';
import { collectImageUrls, transferImages, updateImageUrlsInJson } from '../api/image-transfer';
import {
  determineScaleZoomLevel,
  ensureHttpsProtocol,
  removeSpanTags,
  isNonEmptyString,
  extractProviderUrl,
  detectTheme
} from './utils';
import { EMBEDLY_TYPES } from './storymap-schema';
import { createDerivedTheme } from './storymap-draft-creator';

export class MapJournalConverter {
  private classicJson: ClassicStoryMapJSON;
  private themeId: string;
  private builder: StoryMapJSONBuilder;
  private username: string;
  private token: string;
  private targetStoryId: string;

  constructor(
    classicJson: ClassicStoryMapJSON, 
    themeId: string = 'summit',
    username: string,
    token: string,
    targetStoryId: string
  ) {
    this.classicJson = classicJson;
    this.themeId = themeId;
    this.builder = new StoryMapJSONBuilder(themeId);
    this.username = username;
    this.token = token;
    this.targetStoryId = targetStoryId;
    detectTheme(this.classicJson, 'mapjournal');
  }

  /**
  * Main conversion method
  */
  async convert(): Promise<any> {
    // Get title
    const coverTitle = this.classicJson.values?.title || 'Untitled Story';

    // Attempt custom theme creation
    let customThemeItemId: string | undefined;
    try {
      customThemeItemId = await createDerivedTheme(
        this.username,
        this.token,
        this.classicJson
      );
    } catch (e) {
      console.warn('[MapJournalConverter] Theme creation failed', e);
    }    

    // Map classic layout "side" | "float" -> sidecar subtype
    const classicLayoutId = (this.classicJson.values?.settings?.layout?.id || '').toLowerCase();
    const subtypeMap: Record<string,string> = {
      float: 'floating-panel',
      side: 'side-panel'
    };
    const sidecarSubtype = subtypeMap[classicLayoutId] || 'side-panel';

    // Create sidecar with mapped subtype
    const { sidecarId, slideId: initialSlideId, narrativeId: initialNarrativeId } =
      this.builder.addSidecar(sidecarSubtype);

    // Map classic side panel size/position
    const layoutCfg = this.classicJson.values?.settings?.layoutOptions?.layoutCfg || {};
    const classicSize = (layoutCfg.size || '').toLowerCase(); // small|medium|large
    const classicPos = (layoutCfg.position || '').toLowerCase(); // left|right

    const sizeMap = new Set(['small','medium','large']);
    const sidecarSize = sizeMap.has(classicSize) ? classicSize : 'small';
    const sidecarPos = classicPos === 'right' ? 'end' : 'start'; // default left->start

    const sidecarNode = this.builder.getJson().nodes[sidecarId];
    sidecarNode.data.narrativePanelSize = sidecarSize;
    sidecarNode.data.narrativePanelPosition = sidecarPos;

    // Get sections
    const sections =
      (this.classicJson.values?.story?.sections as ClassicSection[]) || [];

    const hasSections = sections.length > 0;
    console.log("# of Journal sections", sections.length)
    // Process each section as a slide
    for (const section of sections) {
      await this.processSection(section, sidecarId);
    }

    // Remove initial empty slide produced by addSidecar if we added real slides
    if (hasSections) {
      const storymap = this.builder.getJson();
      const sidecarNode = storymap.nodes[sidecarId];
      const idx = sidecarNode.children.indexOf(initialSlideId);
      if (idx > -1) sidecarNode.children.splice(idx, 1);

      // if (sidecarNode.children) {
      //   const index = sidecarNode.children.indexOf(initialSlideId);
      //   if (index !== -1) {
      //     sidecarNode.children.splice(index, 1);
      //   }
      // }
      delete storymap.nodes[initialSlideId];
      delete storymap.nodes[initialNarrativeId];
    }

    // Set cover
    this.builder.setCover(`${coverTitle}`);
    // Set theme
    this.builder.setTheme(customThemeItemId || this.themeId);

    // Image transfer (optional – skip if handled externally)
    // Get the current storymap JSON
    let storymapJson = this.builder.getJson();
    // Collect image URLs 
    const imageUrls = collectImageUrls(storymapJson);
    // Transfer images and get mapping
    if (imageUrls.length > 0 && this.token && this.token !== this.username) {
      const transfers = await transferImages(
        imageUrls,
        this.targetStoryId,
        this.username,
        this.token
      );
      const mapping: Record<string, string> = {};
      transfers.forEach(t => (mapping[t.originalUrl] = t.resourceName));
      storymapJson = updateImageUrlsInJson(storymapJson, mapping);
    }
    return this.builder.getJson();
  }

  /**
   * Process a single section as a sidecar slide
   */
  private async processSection(section: ClassicSection, sidecarId: string): Promise<void> {
    // Get media
    const mediaNodeId = await this.processSectionMedia(section);
    // Get narrative content
    const narrativeContentIds = await this.buildNarrative(section);
    // Add slide to sidecar
    this.builder.addSlideToSidecar(sidecarId, mediaNodeId, narrativeContentIds);
  }

/**
 * Sanitize section title, removing MS Word garbage 
 */
private sanitizeHeading(raw: string): string {
  return raw
    .replace(/<!--\[if[\s\S]*?endif]-->/gi, '')
    .replace(/<xml[\s\S]*?<\/xml>/gi, '')
    .replace(/<\/?style[^>]*>/gi, '')
    .replace(/<!\[endif]-->/gi, '')
    .replace(/<\/?span[^>]*>/gi, '')
    .replace(/<\/?strong[^>]*>/gi, '')
    .replace(/<\/?p[^>]*>/gi, '')
    .replace(/&nbsp;/g, ' ')
    .trim()
    .replace(/&Auml;/gi, 'Ä')
    .replace(/&uuml;/gi, 'ü')
    .replace(/&ouml;/gi, 'ö')
    .replace(/&szlig;/gi, 'ß');
}
/**
 * Sanitize captions 
 */
private sanitizeCaption(raw?: string): string | undefined {
  if (!raw) return undefined;
  const c = raw
    .replace(/<xml[\s\S]*?<\/xml>/gi, '')
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/<\/?span[^>]*>/gi, '')
    .replace(/<\/?p[^>]*>/gi, '')
    .replace(/\sstyle="[^"]*"/gi, '')
    .trim();
  if (!c) return undefined;
  return c;
}

/**
   * Build ordered narrative: title first, then parsed elements
   */
  private async buildNarrative(section: ClassicSection): Promise<string[]> {
    const out: string[] = [];
    const titleHtml = section.title || '';
    // NOTE: Classic sidecar panel size is applied to sidecarNode.data.narrativePanelSize earlier.
    // Node-level sizing should default to 'standard' unless explicitly widened for media.

    if (titleHtml) {
      const cleanedTitle = this.sanitizeHeading(titleHtml);     
      if (isNonEmptyString(cleanedTitle)) {
        // Always use standard node size for narrative text nodes
        const titleId = this.builder.addTextDetached(cleanedTitle, 'h2', 'start');
        out.push(titleId);
      }
    }

    const raw = section.content || '';
    if (!raw) return out;

    // Parse HTML; do NOT inject whole raw content separately (avoid duplicates)
    const parser = new DOMParser();
    const doc = parser.parseFromString(raw, 'text/html');

    for (const el of Array.from(doc.body.children)) {
      const ids = await this.extractElementNodes(el);
      out.push(...ids);
    }
    return out;
  }

  /**
   * Map a single HTML element to detached nodes (wide by default)
   */
  private async extractElementNodes(element: Element): Promise<string[]> {
    const ids: string[] = [];

    // FIGURE (possibly nested)
    if (element.tagName === 'FIGURE') {
      const inner = element.querySelector('figure figure');
      if (inner) return this.extractElementNodes(inner);
      const img = element.querySelector('img');
      if (img) {
        const url = img.getAttribute('src') || '';
        const alt = img.getAttribute('alt') || undefined;
        const captionEl = element.querySelector('figcaption');
        let caption = this.sanitizeCaption(captionEl?.innerHTML || undefined);
        if (captionEl) {
          const rawCaption = captionEl.innerHTML.replace(/&nbsp;/g, ' ').trim();
          if (rawCaption.length > 0) caption = rawCaption;
        }
        ids.push(await this.builder.addImageDetached(url, caption, alt, 'wide'));
      }
      return ids;
    }

    // Skip standalone figcaption (handled in figure)
    if (element.tagName === 'FIGCAPTION') {
      return ids;
    }

    // IMG alone
    if (element.tagName === 'IMG') {
      const url = element.getAttribute('src') || '';
      const alt = element.getAttribute('alt') || undefined;
      ids.push(await this.builder.addImageDetached(url, undefined, alt, 'wide'));
      return ids;
    }

    // Paragraph
    if (element.tagName === 'P') {
      // Inline images
      for (const img of element.querySelectorAll('img')) {
        const url = img.getAttribute('src') || '';
        const alt = img.getAttribute('alt') || undefined;
        ids.push(await this.builder.addImageDetached(url, undefined, alt, 'wide'));
      };
      let html = removeSpanTags(element.innerHTML);
      if (/^(\s|&nbsp;|<br\s*\/?>)*$/i.test(html)) return ids; // empty
      html = html
        .replace(/<xml[\s\S]*?<\/xml>/gi, '')
        .replace(/<!--[\s\S]*?-->/g, '')
        .replace(/&nbsp;/g, ' ')
        .trim();
      if (isNonEmptyString(html)) {
        ids.push(this.builder.addTextDetached(html, 'paragraph', 'start'));
      }
      return ids;
    }

    // Containers that just wrap images/figures/captions
    if (element.classList.contains('image-container') || element.classList.contains('caption')) {
      for (const child of Array.from(element.children)) {
        const childIds = await this.extractElementNodes(child);
        ids.push(...childIds);
      }
      return ids;
    }

    // Iframe/embed container
    if (element.classList.contains('iframe-container')) {
      const iframe = element.querySelector('iframe');
      if (iframe) {
        let url = (iframe.getAttribute('src') || '').trim().replace(/\/$/, '');
        url = ensureHttpsProtocol(url);
        const embedlyType = element.classList.contains('mj-video-by-url') ? 'video' : 'link';
        const display = embedlyType === 'video' ? 'inline' : 'card';
        const providerUrl = extractProviderUrl(url);
        ids.push(
          this.builder.addEmbedDetached(
            url,
            embedlyType,
            display,
            undefined,
            undefined,
            iframe.getAttribute('title') || undefined,
            undefined,
            undefined,
            providerUrl,
            true
          )
        );
      }
      return ids;
    }

    // Generic DIV (avoid double-processing figures/images already handled)
    if (element.tagName === 'DIV') {
      // If it only wraps figures/images, recurse children
      if (
        element.querySelector('figure') &&
        !element.textContent?.trim().replace(/\u00a0/g, '')
      ) {
        for (const child of Array.from(element.children)) {
          const childIds = await this.extractElementNodes(child);
          ids.push(...childIds);
        }
        return ids;
      }
      let html = removeSpanTags(element.innerHTML);
      if (!/^(\s|&nbsp;|<br\s*\/?>)*$/i.test(html)) {
        html = html.replace(/&nbsp;/g, ' ').trim();
        if (isNonEmptyString(html)) {
          ids.push(this.builder.addTextDetached(html, 'paragraph', 'start'));
        }
      }
      return ids;
    }

    return ids;
  }

  /**
   * Process section media (map, image, video, webpage)
   */
  private async processSectionMedia(section: ClassicSection): Promise <string | undefined> {
    const media = section.media;
    if (!media) return undefined;
    const mediaType = media.type;
    if (mediaType === 'webmap') {
      return this.processWebmapMedia(media);
    } else if (mediaType === 'image') {
      return await this.processImageMedia(media);
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
        title: layer.title || '',
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
      'webmap'
    );

    return nodeId;
  }

  /**
   * Process image media
   */
  private async processImageMedia(media: any): Promise<string | undefined> {
    const imageData = media.image;
    if (!imageData) return undefined;

    const url = imageData.url || '';
    const alt = imageData.altText || undefined;
    const caption = imageData.caption || undefined;

    // In browser, we can't download cross-origin images, so just pass URL
    // Add as detached node for sidecar (don't add to story root)
    const nodeId = await this.builder.addImageDetached(url, caption, alt);

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
    const embedlyType = (EMBEDLY_TYPES[mediaType] || 'link') as 'video' | 'link' | 'rich';

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
   * Get list of local images for cleanup
   */
  getLocalImages(): string[] {
    return this.builder.getLocalImages();
  }
}

