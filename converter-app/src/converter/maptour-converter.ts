import type { ClassicStoryMapJSON } from '../types/storymap';
import { StoryMapJSONBuilder } from './storymap-builder';
import {
  createTourMapNode,
  createMapResource,
  createTextNode,
  createImageNode,
  createCarouselNode,
  createTourNode
} from './storymap-schema';
import { transferImages, updateImageUrlsInJson } from '../api/image-transfer';
import { generateNodeId } from './utils';

export class MapTourConverter {
  private username: string;
  private token: string;
  private classicJson: ClassicStoryMapJSON;
  private themeId: string;
  private builder: StoryMapJSONBuilder;
  private imageResourceMap: Record<string, string> = {};

  constructor(classicJson: ClassicStoryMapJSON, themeId: string = 'summit', username: string = '', token: string = '') {
    this.classicJson = classicJson;
    this.themeId = themeId;
    this.username = username;
    this.token = token;
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
    return this.builder.storymap.id;
  }

  async convert(): Promise<any> {
    const values = this.classicJson.values || {};
    const layout = values.layout || 'integrated';
    const title = values.title || 'Untitled Story';
    const subtitle = values.subtitle || '';
    const placesList = values.order || [];
    const features = await this.extractFeatures();

    // Feature ordering
    const featureById: Record<string, any> = {};
    for (const feature of features) {
      const fid = this.getFeatureId(feature.attributes);
      if (fid) featureById[fid] = feature;
    }
    const filteredFeatures = placesList
      .map((p: any) => featureById[String(p.id)])
      .filter(Boolean);

    // Image resource mapping
    const imageMap = this.createImageResourceMap(filteredFeatures);
    this.imageResourceMap = await this.transferImagesFromMap(imageMap);
    console.log('imageMap:', imageMap);
    console.log('imageResourceMap', this.imageResourceMap);

    // Place nodes
    const places: any[] = [];
    const geometries: any[] = [];
    for (let i = 0; i < filteredFeatures.length; i++) {
      const feature = filteredFeatures[i];
      const attrs = feature.attributes || {};
      const titleText = attrs.name || attrs.title || `Place ${i + 1}`;
      const descText = attrs.description || '';
      const isVisible = placesList[i]?.visible !== false;

      const titleNodeId = this.builder.createDetachedNode(
        createTextNode(titleText, 'h3', 'start')
      );
      const contentNodeId = this.builder.createDetachedNode(
        createTextNode(descText, 'paragraph', 'start')
      );
      const contents = [contentNodeId];

      // Media node (image inside carousel)
      const imageUrls: string[] = [];
      ['pic_url', 'thumb_url', 'url', 'URL'].forEach(key => {
        const val = attrs[key];
        if (val && typeof val === 'string' && val.trim()) imageUrls.push(val.trim());
      });

      const imageNodeIds: string[] = [];
      for (const imgUrl of imageUrls) {
        const imageResource = {
          type: "image",
          data: {
            src: imgUrl,
            provider: "uri",
            height: 1024,
            width: 1024
          }
        };
        const imageResourceId = this.builder.addResource(imageResource);
        imageNodeIds.push(
          this.builder.createDetachedNode(
            createImageNode(imageResourceId, undefined, undefined, 'standard', 'start')
          )
        );
      }

      const mediaNodeId = this.builder.createDetachedNode(
        createCarouselNode(imageNodeIds)
      );

      // Geometry
      const x = attrs.long || attrs.longitude || attrs.x;
      const y = attrs.lat || attrs.latitude || attrs.y;
      let geomId = '';
      if (x !== undefined && y !== undefined) {
        let coords: [number, number] = [x, y];
        if (this.isWebMercator(x, y)) {
          coords = this.webMercatorToWgs84(x, y);
        }
        geometries.push({ coords });
        geomId = generateNodeId();
      }

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
    const webmapId = (this.classicJson as any).webmap || (values as any).webmap;
    let tourMapNode = createTourMapNode(geometries);
    if (webmapId) {
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
      '#f9f794',
      'start',
      'large',
      tourType,
      subtype
    );
    const tourNodeId = this.builder.createDetachedNode(tourNode);

    // Add tour and tour-map nodes to story root in correct order
    const rootId = this.getRootNodeId();
    const rootNode = this.builder.getStorymap().nodes[rootId];
    const children = rootNode.children || [];
    const storymapNodes = this.builder.getStorymap().nodes;
    const coverId = children.find((id: string) => storymapNodes[id]?.type === 'storycover');
    const navId = children.find((id: string) => storymapNodes[id]?.type === 'navigation');
    const creditsId = children.find((id: string) => storymapNodes[id]?.type === 'credits');
    this.setRootChildren([coverId, navId, tourNodeId, tourMapNodeId, creditsId].filter(Boolean));

    // Set cover and theme
    this.builder.setCover(`(CONVERSION) ${title}`, subtitle);
    this.builder.setTheme(this.themeId);

    // Update image resource references to match uploaded resources
    const storymapJson = this.builder.getJson();
    const updatedJson = updateImageUrlsInJson(storymapJson, this.imageResourceMap);
    return updatedJson;
  }

  private async extractFeatures(): Promise<any[]> {
    const values = this.classicJson.values || {};
    const webmapJson = (this.classicJson as any).webmapJson || (values as any).webmapJson || {};
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
          const queryUrl = `${url}/query?where=1=1&outFields=*&f=json`;
          const response = await fetch(queryUrl, { headers: { 'User-Agent': 'Mozilla/5.0' } });
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
              const response = await fetch(queryUrl, { headers: { 'User-Agent': 'Mozilla/5.0' } });
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

  private createImageResourceMap(features: any[]): Record<string, { url: string, filename: string }> {
    const imageMap: Record<string, { url: string, filename: string }> = {};
    for (let i = 0; i < features.length; i++) {
      const feature = features[i];
      const fid = this.getFeatureId(feature.attributes);
      const attrs = feature.attributes || {};
      const imgUrl =
        attrs.pic_url ||
        attrs.thumb_url ||
        attrs.url ||
        attrs.URL ||
        '';
      if (fid && imgUrl) {
        imageMap[fid] = {
          url: imgUrl,
          filename: this.getImageFilenameForFeature(feature, i)
        };
      }
    }
    return imageMap;
  }

  private async transferImagesFromMap(
    imageMap: Record<string, { url: string, filename: string }>
  ): Promise<Record<string, string>> {
    const imageUrls = Object.values(imageMap).map(entry => entry.url);
    const targetItemId = this.getStorymapId();
    const transferResultsArray = await transferImages(
      imageUrls,
      targetItemId,
      this.username,
      this.token
    );
    const transferResults: Record<string, string> = {};
    for (const result of transferResultsArray) {
      transferResults[result.originalUrl] = result.resourceName;
    }
    return transferResults;
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

  private getAttrFromList(attrs: any, keys: string[], def: string = ''): string {
    for (const key of keys) {
      const value = attrs[key];
      if (value !== undefined && String(value).trim() !== '') return value;
    }
    return def;
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

  private getImageFilenameForFeature(feature: any, idx: number): string {
    const attrs = feature.attributes || {};
    const imgUrl =
      attrs.url ||
      attrs.URL ||
      attrs.pic_url ||
      attrs.PIC_URL ||
      '';
    if (imgUrl && typeof imgUrl === 'string') {
      const parts = imgUrl.split(/[\/]/);
      const filename = parts[parts.length - 1].split('?')[0];
      if (filename) return filename;
    }
    return `place_${idx + 1}.jpg`;
  }
}