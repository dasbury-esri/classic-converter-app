/**
 * StoryMap JSON Builder
 * Builds StoryMap JSON structure without using the Python API
 * Ported from StoryMapJSONBuilder class in converter_json.py
 */

import type {
  StoryMapNode,
  StoryMapResource,
  Extent,
  Viewpoint,
  MapLayer
} from '../types/storymap';
import {
  createBaseStorymapJson,
  createTextNode,
  createImageNode,
  createImageResource,
  createMapNode,
  createMapResource,
  createEmbedNode,
  createGalleryNode,
  createSeparatorNode,
  createSidecarStructure,
  createSlideStructure,
  addChildToNode,
  insertNodeBeforeCredits,
  setCoverData,
  setTheme
} from './storymap-schema';
import { generateNodeId, generateResourceId } from './utils';

export class StoryMapJSONBuilder {
  private storymap: any;
  public localImages: string[] = [];

  constructor(_themeId: string = 'summit') {
    this.storymap = createBaseStorymapJson();
  }

  /**
   * Get the complete StoryMap JSON
   */
  getJson(): any {
    return this.storymap;
  }

  /**
   * Add a node to the story
   */
  addNode(node: StoryMapNode, parentId?: string): string {
    const nodeId = generateNodeId();
    this.storymap.nodes[nodeId] = node;

    if (parentId) {
      addChildToNode(this.storymap, parentId, nodeId);
    } else {
      // Add to story root before credits
      insertNodeBeforeCredits(this.storymap, nodeId);
    }

    return nodeId;
  }

  /**
   * Create a detached node (not added to any parent)
   * Useful for sidecar media
   */
  createDetachedNode(node: StoryMapNode): string {
    const nodeId = generateNodeId();
    this.storymap.nodes[nodeId] = node;
    return nodeId;
  }

  /**
   * Add a resource to the story
   */
  addResource(resource: StoryMapResource): string {
    const resourceId = generateResourceId();
    this.storymap.resources[resourceId] = resource;
    return resourceId;
  }

  /**
   * Add a text node
   */
  addText(
    text: string,
    style: string = 'paragraph',
    alignment: string = 'start',
    parentId?: string
  ): string {
    const node = createTextNode(text, style, alignment);
    return this.addNode(node, parentId);
  }

  /**
   * Add a detached text node (not added to story root, useful for sidecars)
   */
  addTextDetached(
    text: string,
    style: string = 'paragraph',
    alignment: string = 'start'
  ): string {
    const node = createTextNode(text, style, alignment);
    return this.createDetachedNode(node);
  }

  /**
   * Add an image node with resource
   */
  addImage(
    imagePath: string,
    caption?: string,
    alt?: string,
    display: string = 'standard',
    floatAlignment: string = 'start',
    parentId?: string,
    isItemResource: boolean = false
  ): string {
    // Create resource
    const resource = createImageResource(imagePath, isItemResource);
    const resourceId = this.addResource(resource);

    // Create node
    const node = createImageNode(resourceId, caption, alt, display, floatAlignment);
    return this.addNode(node, parentId);
  }

  /**
   * Add a detached image node (not added to story root, useful for sidecars)
   */
  addImageDetached(
    imagePath: string,
    caption?: string,
    alt?: string,
    display: string = 'standard',
    floatAlignment: string = 'start',
    isItemResource: boolean = false
  ): string {
    // Create resource
    const resource = createImageResource(imagePath, isItemResource);
    const resourceId = this.addResource(resource);

    // Create node
    const node = createImageNode(resourceId, caption, alt, display, floatAlignment);
    return this.createDetachedNode(node);
  }

  /**
   * Add a map node with resource
   */
  addMap(
    mapItemId: string,
    extent?: Extent,
    viewpoint?: Viewpoint,
    zoom?: number,
    mapLayers?: MapLayer[],
    itemType: string = 'Web Map',
    parentId?: string
  ): { nodeId: string; resourceId: string } {
    // Create resource
    const resource = createMapResource(mapItemId, itemType);
    const resourceId = this.addResource(resource);

    // Create node
    const node = createMapNode(resourceId, extent, viewpoint, zoom, mapLayers);
    const nodeId = this.addNode(node, parentId);

    return { nodeId, resourceId };
  }

  /**
   * Add a detached map node (not added to story root, useful for sidecars)
   */
  addMapDetached(
    mapItemId: string,
    extent?: Extent,
    viewpoint?: Viewpoint,
    zoom?: number,
    mapLayers?: MapLayer[],
    itemType: string = 'Web Map'
  ): { nodeId: string; resourceId: string } {
    // Create resource
    const resource = createMapResource(mapItemId, itemType);
    const resourceId = this.addResource(resource);

    // Create node
    const node = createMapNode(resourceId, extent, viewpoint, zoom, mapLayers);
    const nodeId = this.createDetachedNode(node);

    return { nodeId, resourceId };
  }

  /**
   * Add an embed node
   */
  addEmbed(
    url: string,
    embedType: string = 'video',
    display: string = 'card',
    caption?: string,
    alt?: string,
    title?: string,
    description?: string,
    thumbnailUrl?: string,
    providerUrl?: string,
    parentId?: string
  ): string {
    const node = createEmbedNode(
      url,
      embedType,
      display,
      caption,
      alt,
      title,
      description,
      thumbnailUrl,
      providerUrl
    );
    return this.addNode(node, parentId);
  }

  /**
   * Add a detached embed node (not added to story root, useful for sidecars)
   */
  addEmbedDetached(
    url: string,
    embedType: string = 'video',
    display: string = 'card',
    caption?: string,
    alt?: string,
    title?: string,
    description?: string,
    thumbnailUrl?: string,
    providerUrl?: string
  ): string {
    const node = createEmbedNode(
      url,
      embedType,
      display,
      caption,
      alt,
      title,
      description,
      thumbnailUrl,
      providerUrl
    );
    return this.createDetachedNode(node);
  }

  /**
   * Add a gallery node with image nodes
   */
  addGallery(
    imagePaths: string[],
    caption?: string,
    alt?: string,
    layout: string = 'square-dynamic',
    parentId?: string,
    isItemResource: boolean = false
  ): string {
    // Create image nodes for each image
    const imageNodeIds: string[] = [];
    for (const imagePath of imagePaths) {
      const nodeId = this.addImage(imagePath, undefined, undefined, 'standard', 'start', undefined, isItemResource);
      imageNodeIds.push(nodeId);
    }

    // Create gallery node
    const node = createGalleryNode(imageNodeIds, caption, alt, layout);
    return this.addNode(node, parentId);
  }

  /**
   * Add a detached gallery node (not added to story root, useful for sidecars)
   */
  addGalleryDetached(
    imagePaths: string[],
    caption?: string,
    alt?: string,
    layout: string = 'square-dynamic',
    isItemResource: boolean = false
  ): string {
    // Create detached image nodes for each image
    const imageNodeIds: string[] = [];
    for (const imagePath of imagePaths) {
      const nodeId = this.addImageDetached(imagePath, undefined, undefined, 'standard', 'start', isItemResource);
      imageNodeIds.push(nodeId);
    }

    // Create gallery node
    const node = createGalleryNode(imageNodeIds, caption, alt, layout);
    return this.createDetachedNode(node);
  }

  /**
   * Add a separator node
   */
  addSeparator(parentId?: string): string {
    const node = createSeparatorNode();
    return this.addNode(node, parentId);
  }

  /**
   * Add a sidecar structure
   */
  addSidecar(sidecarType: string = 'docked-panel'): {
    sidecarId: string;
    slideId: string;
    narrativeId: string;
  } {
    const { sidecarId, slideId, narrativeId, nodes } = createSidecarStructure(sidecarType);

    // Add all nodes
    Object.assign(this.storymap.nodes, nodes);

    // Insert sidecar before credits
    insertNodeBeforeCredits(this.storymap, sidecarId);

    return { sidecarId, slideId, narrativeId };
  }

  /**
   * Add a slide to an existing sidecar
   */
  addSlideToSidecar(
    sidecarId: string,
    mediaNodeId?: string,
    narrativeContentIds?: string[]
  ): { slideId: string; narrativeId: string } {
    const { slideId, narrativeId, nodes } = createSlideStructure();

    // Add narrative content
    if (narrativeContentIds) {
      nodes[narrativeId].children = narrativeContentIds;
    }

    // Add media node as child of slide
    if (mediaNodeId) {
      nodes[slideId].children!.push(mediaNodeId);
    }

    // Add nodes to storymap
    Object.assign(this.storymap.nodes, nodes);

    // Add slide to sidecar
    addChildToNode(this.storymap, sidecarId, slideId);

    return { slideId, narrativeId };
  }

  /**
   * Set cover information
   */
  setCover(
    title: string,
    summary: string = '',
    byLine: string = '',
    imagePath?: string
  ): void {
    let imageResourceId: string | undefined;

    if (imagePath) {
      const resource = createImageResource(imagePath);
      imageResourceId = this.addResource(resource);
    }

    setCoverData(this.storymap, title, summary, byLine, imageResourceId);
  }

  /**
   * Set story theme
   */
  setTheme(themeId: string): void {
    setTheme(this.storymap, themeId);
  }

  /**
   * Get list of locally downloaded images for cleanup
   */
  getLocalImages(): string[] {
    return this.localImages;
  }
}

