import type { ClassicStoryMapJSON } from '../types/storymap';
import type { MapTourValues } from '../types/storymap';

import { StoryMapJSONBuilder } from './storymap-builder';
import {
  createTourMapNode,
  createMapResource,
  createTextNode,
  createImageNode,
  createCarouselNode,
  createTourNode,
  createCreditsNode
} from './storymap-schema';
import { transferImage } from '../api/image-transfer';
import { 
  generateNodeId, 
  generateUUID,
  getAttrFromList,
  ensureHttpsProtocol 
} from './utils';

// Attribute key lists (update here as needed)
const IMAGE_URL_KEYS = ['pic_url', 'Pic_url', 'PIC_URL', 'url', 'Url', 'URL'] as const;
const THUMB_URL_KEYS = ['thumb_url', 'Thumb_url', 'THUMB_URL'] as const;
const TITLE_KEYS = ['name', 'Name', 'NAME', 'title', 'Title', 'TITLE'] as const;
const DESC_KEYS = [
  'description', 'Description', 'DESCRIPTION',
  'desc', 'Desc', 'DESC', 'desc1', 'Desc1', 'DESC1',
  'caption', 'Caption', 'CAPTION', 'FULL_Caption'
] as const;
const ATTR_KEYS = ['PHOTO_CREDIT', 'photo_credit', 'credit', 'attribution'] as const;
const LON_KEYS = ['long', 'Long', 'LONG', 'LON', 'longitude', 'Longitude', 'LONGITUDE', 'x'] as const;
const LAT_KEYS = ['lat', 'Lat', 'LAT', 'latitude', 'Latitude', 'LATITUDE', 'y'] as const;

export class MapTourConverter {
  private targetStoryId: string;
  private username: string;
  private token: string;
  private classicJson: ClassicStoryMapJSON;
  private themeId: string;
  private builder: StoryMapJSONBuilder;
  // Map featureId to uploaded image/thumb resource info
  private uploadedResources: Record<string, {
    imageUrl: string;
    thumbUrl: string;
    imageFilename: string;
    thumbFilename: string;
    imageResourceId?: string;
    thumbResourceId?: string;
  }> = {};

  constructor(classicJson: ClassicStoryMapJSON, themeId: string = 'summit', username: string = '', token: string = '', targetStoryId: string = '') {
    console.log('[MapTourConverter] Constructor targetStoryId:', targetStoryId);
    this.classicJson = classicJson;
    this.themeId = themeId;
    this.username = username;
    this.token = token;
    this.targetStoryId = targetStoryId;
    this.builder = new StoryMapJSONBuilder(themeId);
    this.detectTheme();
  }

  private detectTheme(): void {
    try {
      const themeMajor = this.classicJson.values?.settings?.theme?.colors?.themeMajor;
      const themeMapping: Record<string, string> = {
        dark: 'obsidian',
        light: 'summit'
      };
      if (themeMajor && themeMapping[themeMajor]) {
        this.themeId = themeMapping[themeMajor];
      }
    } catch {
      // Use default theme
    }
  }

  private getRootNodeId(): string {
    return this.builder.getStorymap().root;
  }

  private setRootChildren(children: string[]): void {
    this.builder.getStorymap().nodes[this.getRootNodeId()].children = children;
  }

  private getStorymapId(): string {
    console.log('[MapTourConverter] getStorymapId:', this.targetStoryId);
    return this.targetStoryId;
  }

  async convert(): Promise<any> {
    const values = this.classicJson.values || {};
    const mtValues = values as MapTourValues;
    // Directly extract layout, subtitle, and order from values
    const layout = mtValues.layout || 'integrated'; // classic options were; "three-panel", "integrated", "side-panel"
    const title = mtValues.title || 'Untitled Story';
    const subtitle = mtValues.subtitle || '';
    const placesList = mtValues.order || mtValues.places || [];
    const placardPosition = mtValues.placardPosition || 'start';
    const headerColor = mtValues.colors ? mtValues.colors.split(';')[0] : '#FFFFFF'; // fallback to white. Classic Map Tour had a very simple theme "header". "content" (i.e. slide) and "footer" (i.e. silde carousel)
    const slideColor = mtValues.colors ? mtValues.colors.split(';')[1] : '#FFFFFF'; // thumbnail background color
    const carouselColor = mtValues.colors ? mtValues.colors.split(';')[2] : '#FFFFFF'; // thumbnail carousel background color
    const zoomLevel = mtValues.zoomLevel || ''; // map zoom level after navigating to a point. Need to translate the zoomLevel [0-22?] to a scale for AGSM (enum?) 
    const locateButton = mtValues.locationButton || ''; // option to show the location button in the UI
    const customLogoImageUrl = mtValues.logoURL || '';
    const customLogoClickThroughLink = mtValues.logoTarget || '';
    const customHeaderText = mtValues.headerLinkText || '';
    const customHeaderClickThroughLink = mtValues.headerLinkUrl || '';
    const socialButtonFacebook = mtValues.social.facebook || ''; // boolean
    const socialButtonTwitter = mtValues.social.twitter || ''; // boolean
    const socialButtonBitly = mtValues.social.bitly || ''; // boolean
    const firstRecordAsIntro = mtValues.firstRecordAsIntro || ''; // option to make the first feature/point a splash page. During conversion we can make this data the cover.
    const accentColor = '#f9f794'; // in classic Map Tour, each point could have a customized marker color. AGSM doesn't have this option. fallback color
    const features = await this.extractFeatures();

    // Track node IDs to enforce proper order
    const orderedNodeIds: string[] = [];
    // Create nodes
    const rootId = this.getRootNodeId();
    const storymapNodes = this.builder.getStorymap().nodes;
    const children = storymapNodes[rootId].children || [];
    const coverId = Object.keys(storymapNodes).find(id => storymapNodes[id]?.type === 'storycover');
    const navId = Object.keys(storymapNodes).find(id => storymapNodes[id]?.type === 'navigation');
  // Create credits node and its children
  const { creditsId, childIds, nodes: creditsNodes } = createCreditsNode('', '', '');
  // Add creditsNodes to storymap nodes
  Object.assign(storymapNodes, creditsNodes);

  // Ensure storycover and navigation are first
  if (coverId) orderedNodeIds.push(coverId);
  if (navId) orderedNodeIds.push(navId);

  const rootChildren = storymapNodes[rootId].children || [];
  const oldCreditsId = rootChildren.find(id => storymapNodes[id]?.type === 'credits' && id !== creditsId);

  if (oldCreditsId) {
    // Remove from nodes
    delete storymapNodes[oldCreditsId];
    // Remove from root children
    const idx = rootChildren.indexOf(oldCreditsId);
    if (idx !== -1) rootChildren.splice(idx, 1);
  }

    // Feature ordering
    const featureById: Record<string, any> = {};
    for (const feature of features) {
      const fid = this.getFeatureId(feature.attributes);
      if (fid) featureById[fid] = feature;
    }
    const filteredFeatures = placesList
      .map((p: any) => featureById[String(p.id)])
      .filter(Boolean);

    console.log("Number of places:", filteredFeatures.length)  

    // 1. Build image/thumb map and upload resources
    // For each place, add image, carousel, title, contents nodes in order
    for (let i = 0; i < filteredFeatures.length; i++) {
      const feature = filteredFeatures[i];
      const fid = this.getFeatureId(feature.attributes);
      if (!fid) continue;
      const attrs = feature.attributes || {};
      const imageUrl = getAttrFromList(attrs, IMAGE_URL_KEYS, '');
      const thumbUrl = getAttrFromList(attrs, THUMB_URL_KEYS, '');
      // Generate unique filenames
      const imageFilename = this.generateUniqueFilename(fid, 'image', imageUrl);
      const thumbFilename = thumbUrl ? this.generateUniqueFilename(fid, 'thumb', thumbUrl) : '';
      // Upload image
      let imageResourceId: string | undefined;
      if (imageUrl) {
        console.log('[MapTourConverter] Preparing to transfer image:', { imageUrl, imageFilename });
        const imageTransferResult = await this.transferSingleImage(imageUrl, imageFilename);
        console.log('[MapTourConverter] Image transfer result:', imageTransferResult);
        imageResourceId = this.builder.addResource({
          type: "image",
          data: {
            resourceId: imageTransferResult.resourceName,            
            provider: "item-resource",
            height: 1024,
            width: 1024
          }
        });
        console.log('[MapTourConverter] Added image resource:', { imageResourceId, resourceName: imageTransferResult.resourceName });
      }
      // Upload thumbnail
      let thumbResourceId: string | undefined;
      if (thumbUrl) {
        // const thumbTransferResult = await this.transferSingleImage(thumbUrl, thumbFilename);
        // thumbResourceId = this.builder.addResource({
        //   type: "image",
        //   data: {
        //     provider: "item-resource",
        //     resourceId: thumbTransferResult.resourceName,
        //     height: 256,
        //     width: 256
        //   }
        // });
      }
      this.uploadedResources[fid] = {
        imageUrl,
        thumbUrl,
        imageFilename,
        thumbFilename,
        imageResourceId,
        thumbResourceId
      };
    }

    // 2. Build place nodes with carousel media
    const places: any[] = [];
    // Build geometries for tour-map
    const geometries: Record<string, any> = {};   
    
    for (let i = 0; i < filteredFeatures.length; i++) {
      const feature = filteredFeatures[i];
      const attrs = feature.attributes || {};
      const fid = this.getFeatureId(attrs);
      const titleText = getAttrFromList(attrs, TITLE_KEYS, `Place ${i + 1}`);
      const descText = getAttrFromList(attrs, DESC_KEYS, '');
      const attributionText = getAttrFromList(attrs, ATTR_KEYS, '');
      const isVisible = placesList[i]?.visible !== false;
      const coords = this.getFeatureCoords(feature);
      if (!coords) continue; // skip if no valid coordinates 
      let { long, lat } = coords;
      if (this.isWebMercator(long, lat)) {
        [long, lat] = this.webMercatorToWgs84(long, lat);
      } 

      const resourceInfo = fid ? this.uploadedResources[fid] : undefined;

      const imageNodeId = resourceInfo?.imageResourceId
        ? this.builder.createDetachedNode(
            createImageNode(resourceInfo.imageResourceId, undefined, undefined, 'standard', 'start')
          )
        : undefined;

      const thumbNodeId = resourceInfo?.thumbResourceId
        ? this.builder.createDetachedNode(
            createImageNode(resourceInfo.thumbResourceId, undefined, undefined, 'standard', 'start')
          )
        : undefined;

      const imageNodeIds: string[] = [];
      if (imageNodeId) imageNodeIds.push(imageNodeId);
      if (thumbNodeId) imageNodeIds.push(thumbNodeId);

      const mediaNodeId = this.builder.createDetachedNode(
        createCarouselNode(imageNodeIds)
      );
      const titleNodeId = this.builder.createDetachedNode(
        createTextNode(titleText, 'h3', 'start')
      );
      const contentNodeId = this.builder.createDetachedNode(
        createTextNode(descText, 'paragraph', 'start')
      );
      const contents = [contentNodeId];

      // Geometry
      let geomId = generateUUID();
      if (coords && coords.long !== undefined && coords.lat !== undefined) {
        geometries[geomId] = {
          id: geomId,
          type: "POINT_NUMBERED_TOUR",
          nodes: [{ long, lat }],
          scale: 4514,
          viewpoint: {}
        };
      }
  // Push its NodeIds to orderedNodeIds in the proper order
  if (imageNodeId) orderedNodeIds.push(imageNodeId);
  if (thumbNodeId) orderedNodeIds.push(thumbNodeId);
  orderedNodeIds.push(mediaNodeId);
  orderedNodeIds.push(titleNodeId);
  orderedNodeIds.push(contentNodeId);

      // Place node
      places.push({
        id: generateNodeId(),
        featureId: geomId,
        contents,
        media: mediaNodeId,
        title: titleNodeId,
        config: isVisible ? undefined : { isHidden: true }
      });
    }

    // Basemap resource creation and assignment
    const webmapJson = (this.classicJson as any).webmapJson || (mtValues as any).webmapJson || {};
    const webmapId = (this.classicJson as any).webmap || (mtValues as any).webmap;
    let tourMapNode = createTourMapNode(geometries);
    if (webmapJson && typeof webmapJson.version === 'string' && parseFloat(webmapJson.version) < 2.0) {
      // Use basemap name for old webmaps
      const basemapTitle = webmapJson.baseMap?.title?.toLowerCase() || 'topographic';
      tourMapNode.data.basemap = {
        type: 'name',
        value: basemapTitle
      };
    } else if (webmapId) {
      // Use webmap resource for newer webmaps
      const basemapResourceId = this.builder.addResource(createMapResource(webmapId));
      tourMapNode.data.basemap = {
        type: 'resource',
        value: basemapResourceId
      };
    }
    const tourMapNodeId = this.builder.createDetachedNode(tourMapNode);
  
    // Tour node (detached)
    const tourType =
      layout === 'integrated'
        ? 'guided-tour'
        : layout === 'three-panel' || layout === 'side-panel'
        ? 'guided-tour'
        : 'explorer';
    const subtype =
      layout === 'integrated'
        ? 'map-focused'
        : layout === 'three-panel' || layout === 'side-panel'
        ? 'media-focused'
        : 'grid';

    const tourNode = createTourNode(
      places,
      tourMapNodeId,
      accentColor,
      placardPosition,
      'large',
      tourType,
      subtype
    );
    const tourNodeId = this.builder.createDetachedNode(tourNode);

    // Add tour-map and tour nodes
    orderedNodeIds.push(tourMapNodeId);
    orderedNodeIds.push(tourNodeId);

    // Add credits children and credits node immediately before story node
    for (const childId of childIds) {
      orderedNodeIds.push(childId);
    }
    orderedNodeIds.push(creditsId);
    orderedNodeIds.push(rootId);

    // Rebuild nodes object in this order
    const nodes = this.builder.getStorymap().nodes;
    const reordered: Record<string, any> = {};
    for (const id of orderedNodeIds) {
      if (nodes[id]) reordered[id] = nodes[id];
    }
    // Optionally, add any remaining nodes not referenced (orphaned nodes)
    for (const id of Object.keys(nodes)) {
      if (!reordered[id]) reordered[id] = nodes[id];
    }
    this.builder.getStorymap().nodes = reordered;

  this.setRootChildren([coverId, navId, tourNodeId, tourMapNodeId, creditsId].filter(Boolean));

    // Set cover and theme
    this.builder.setCover(`(CONVERSION) ${title}`, subtitle);
    this.builder.setTheme(this.themeId);

    const storymapJson = this.builder.getJson();
    return storymapJson;
  }

  private async extractFeatures(): Promise<any[]> {
    const values = this.classicJson.values || {};
    const webmapJson = (this.classicJson as any).webmapJson || (mtValues as any).webmapJson || {};
    const layers = webmapJson.operationalLayers || [];
    const sourceLayer = (this.classicJson as any).sourceLayer || (values as any).sourceLayer;
    let mapTourLayer: any = null;
    for (const layer of layers) {
      if ((layer.title || '').toLowerCase() === 'map tour layer') {
        mapTourLayer = layer;
        break;
      }
    }
    if (mapTourLayer) {
      if (mapTourLayer.featureCollection) {
        const fc = mapTourLayer.featureCollection;
        for (const fcLayer of fc.layers || []) {
          if (fcLayer.featureSet) {
            const feats = fcLayer.featureSet.features || [];
            return feats;
          }
        }
      }
      const featureServiceUrl = mapTourLayer.url || mapTourLayer.URL;
      if (featureServiceUrl) {
        let url = featureServiceUrl;
        if (url.startsWith('http://')) url = 'https://' + url.slice(7);
        try {
          // Direct fetch
          const queryUrl = `${url}/query?where=1=1&outFields=*&f=json`;
          // const response = await fetch(queryUrl, { headers: { 'User-Agent': 'Mozilla/5.0' } });
          const httpsUrl = ensureHttpsProtocol(queryUrl)
          const proxyUrl = `http://localhost:3001/proxy-feature?url=${encodeURIComponent(httpsUrl)}`;
          const response = await fetch(proxyUrl);
          if (response.ok) {
            const fsJson = await response.json();
            if (fsJson.features) {
              return fsJson.features;
            }
          }
        } catch (err) {
          console.error('Error fetching features from Map Tour feature service:', err);
        }
      }
    } else if (sourceLayer) {
      for (const layer of layers) {
        const layerId = layer.id || '';
        if (layerId.includes(sourceLayer) || sourceLayer.includes(layerId)) {
          if (layer.featureCollection) {
            const fc = layer.featureCollection;
            for (const fcLayer of fc.layers || []) {
              if (fcLayer.featureSet) {
                const feats = fcLayer.featureSet.features || [];
                return feats;
              }
            }
          }
          const featureServiceUrl = layer.url || layer.URL;
          if (featureServiceUrl) {
            let url = featureServiceUrl;
            if (url.startsWith('http://')) url = 'https://' + url.slice(7);
            try {
              const queryUrl = `${url}/query?where=1=1&outFields=*&f=json`;
              // const response = await fetch(queryUrl, { headers: { 'User-Agent': 'Mozilla/5.0' } });
              const httpsUrl = ensureHttpsProtocol(queryUrl)
              const proxyUrl = `http://localhost:3001/proxy-feature?url=${encodeURIComponent(httpsUrl)}`;
              const response = await fetch(proxyUrl);
              if (response.ok) {
                const fsJson = await response.json();
                if (fsJson.features) {
                  return fsJson.features;
                }
              }
            } catch (err) {
              console.error('Error fetching features from fallback feature service:', err);
            }
          }
          break;
        }
      }
    }
    return [];
  }

  private getFeatureId(attrs: any): string | undefined {
    for (const key of [
      '__OBJECTID',
      'objectid',
      'id',
      'ID',
      'FID',
      'fid',
      'ObjectID',
      'Object_Id',
      'OBJECTID',
      'OBJECTID_1'
    ]) {
      if (attrs[key] !== undefined && attrs[key] !== null) return String(attrs[key]).trim();
    }
    return undefined;
  }

  private isWebMercator(x: number, y: number): boolean {
    return Math.abs(x) > 180 || Math.abs(y) > 90;
  }

  private webMercatorToWgs84(x: number, y: number): [number, number] {
    const R_MAJOR = 6378137.0;
    const lon = (x / R_MAJOR) * 180.0 / Math.PI;
    let lat = (y / R_MAJOR) * 180.0 / Math.PI;
    lat = 180.0 / Math.PI * (2 * Math.atan(Math.exp(lat * Math.PI / 180.0)) - Math.PI / 2.0);
    return [lon, lat];
  }

  // Generate a unique filename for image or thumb
  private generateUniqueFilename(fid: string, type: 'image' | 'thumb', url: string): string {
    const extMatch = url.match(/\.([a-zA-Z0-9]+)(\?|$)/);
    const ext = extMatch ? extMatch[1] : 'jpg';
    const uid = this.randomUrlSafeBase64String();
    const fidPadded = fid.padStart(3, '0');
    return `place_${fidPadded}_${type}_${uid}.${ext}`;
  }

  // Secure random UID generator
  private randomUrlSafeBase64String(): string {
    const bytes = new Uint8Array(4);
    if (typeof window !== 'undefined' && window.crypto) {
      window.crypto.getRandomValues(bytes);
      return btoa(String.fromCharCode(...bytes))
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=+$/, '')
        .slice(0, 6);
    } else {
      // Node.js fallback
      // Use Buffer and crypto
      const crypto = require('crypto');
      crypto.randomFillSync(bytes);
      return Buffer.from(bytes)
        .toString('base64')
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=+$/, '')
        .slice(0, 6);
    }
  }

  // Transfer a single image and return transfer result
  private async transferSingleImage(url: string, filename: string): Promise<{ originalUrl: string; resourceName: string; isTransferred: boolean }> {
    // You may want to pass filename to transferImage if your API supports it
    // Otherwise, transferImage will generate a resource name
    if (!this.getStorymapId()) {
      throw new Error("Target StoryMap item ID is missing!");
    }
    return await transferImage(url, this.getStorymapId(), this.username, this.token, filename);
  }

  // Robustly get coordinates
  private getFeatureCoords(feature: any): { long: number, lat: number } | undefined {
    const attrs = feature.attributes || {};
    // Try attribute-based extraction
    const longStr = getAttrFromList(attrs, LON_KEYS, '');
    const latStr = getAttrFromList(attrs, LAT_KEYS, '');
    let long = Number(longStr);
    let lat = Number(latStr);

    // If valid numbers, use them
    if (!isNaN(long) && !isNaN(lat) && long !== 0 && lat !== 0) {
      return { long, lat };
    }

    // Fallback to geometry object
    if (feature.geometry && typeof feature.geometry.x === 'number' && typeof feature.geometry.y === 'number') {
      return { long: feature.geometry.x, lat: feature.geometry.y };
    }

    // No valid coordinates found
    console.warn("No valid coordinates found for feature", feature);
    return undefined;
  }

}