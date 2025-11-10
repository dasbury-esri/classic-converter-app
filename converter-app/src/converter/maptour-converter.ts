import type { ClassicStoryMapJSON } from '../types/storymap';
import { StoryMapJSONBuilder } from './storymap-builder';
import {
  createTourMapNode,
  createTourNode,
  createTourMapGeometry,
  createTextNode,
  createImageNode,
  createCarouselNode,
  createMapResource
} from './storymap-schema';
import { generateNodeId } from './utils';
import { transferImages } from '../api/image-transfer';

export class MapTourConverter {
  private username: string;
  private token: string;
  // Helper to get root node id
  private getRootNodeId(): string {
  // @ts-ignore
  return this.builder.getStorymap().root;
  }

  // Helper to set root children
  private setRootChildren(children: string[]): void {
  // @ts-ignore
  this.builder.getStorymap().nodes[this.getRootNodeId()].children = children;
  }

  // Helper to get storymap id
  private getStorymapId(): string {
    // @ts-ignore
    return this.builder.storymap.id;
  }
  private classicJson: ClassicStoryMapJSON;
  private themeId: string;
  private builder: StoryMapJSONBuilder;
  private imageResourceMap: Record<string, string> = {};

  constructor(classicJson: ClassicStoryMapJSON, themeId: string = 'summit') {
    this.classicJson = classicJson;
    this.themeId = themeId;
    this.builder = new StoryMapJSONBuilder(themeId);
    this.detectTheme();
  }

  private detectTheme(): void {
    try {
      const themeMajor =
        this.classicJson.values?.settings?.theme?.colors?.themeMajor;
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

  async convert(): Promise<any> {
    const values = this.classicJson.values || {};
    const title = values.title || 'Untitled MapTour';
    const subtitle = (values as any).subtitle || '';
    const layout = (values as any).layout || 'three-panel';
    const placesList = (values as any).order || [];
    const features = await this.extractFeatures();
    if (!features || features.length === 0) {
      throw new Error('No features found in classic Map Tour data. Please check the source or webmap configuration.');
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

    // Log to browser console
    console.log('filteredFeatures:', filteredFeatures);

    // Create image map
    const imageMap = await this.createImageResourceMap(filteredFeatures);
    console.log('imageMap:', imageMap);

    // Transfer images
    const imageResourceMap = await this.transferImagesFromMap(imageMap);
    console.log('imageResourceMap:', imageResourceMap);

    // Geometry creation
    const geometries: Record<string, any> = {};
    const places: any[] = [];
    for (let i = 0; i < filteredFeatures.length; i++) {
      const feature = filteredFeatures[i];
      const placeEntry = placesList[i];
      const isVisible = placeEntry.visible !== false;
      const geomId = generateNodeId();
      const { x, y } = feature.geometry;
      const [long, lat] = this.isWebMercator(x, y)
        ? this.webMercatorToWgs84(x, y)
        : [x, y];
      geometries[geomId] = createTourMapGeometry(geomId, long, lat, 'POINT_NUMBERED_TOUR');

      // Place content nodes (detached)
      const attrs = feature.attributes || {};
      const titleText = this.getAttrFromList(attrs, ['name', 'NAME', 'Name']);
      const descText = this.getAttrFromList(attrs, [
        'description',
        'DESCRIPTION',
        'Description',
        'DESC1',
        'caption',
        'CAPTION',
        'Caption',
        'FULL_Caption'
      ]);
      const attributionText = this.getAttrFromList(attrs, ['PHOTO_CREDIT']);
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
    // Find cover, navigation, credits node IDs
    const children = rootNode.children || [];
  const storymapNodes = this.builder.getStorymap().nodes;
  const coverId = children.find((id: string) => storymapNodes[id]?.type === 'storycover');
  const navId = children.find((id: string) => storymapNodes[id]?.type === 'navigation');
  const creditsId = children.find((id: string) => storymapNodes[id]?.type === 'credits');
    // Set correct order: cover, navigation, tour, tour-map, credits
    this.setRootChildren([coverId, navId, tourNodeId, tourMapNodeId, creditsId].filter(Boolean));

    // Set cover and theme
    this.builder.setCover(`(CONVERSION) ${title}`, subtitle);
    this.builder.setTheme(this.themeId);
      // Update image resource references to match uploaded resources
      const storymapJson = this.builder.getJson();
      // Use imageResourceMap to update resource references
      // updateImageUrlsInJson expects a map of originalUrl -> resourceName
      // If transfer failed, resourceName will be the original URL
      // This ensures resourceId/provider are set correctly
      // (import from image-transfer)
      // @ts-ignore
      const { updateImageUrlsInJson } = await import('../api/image-transfer');
      const updatedJson = updateImageUrlsInJson(storymapJson, this.imageResourceMap);
      return updatedJson;
    }
  private async extractFeatures(): Promise<any[]> {
    const values = this.classicJson.values || {};
    console.log('classicItemValues:', values);
    const webmapJson = (this.classicJson as any).webmapJson || (values as any).webmapJson || {};
    console.log('webmapJson:', webmapJson);
    const layers = webmapJson.operationalLayers || [];
    console.log('operationalLayers:', layers);
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
            if (feats.length === 0) {
              console.error('No features found in Map Tour featureCollection.');
            }
            return feats;
          }
        }
        console.error('No featureSet found in Map Tour featureCollection.');
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
              if (fsJson.features.length === 0) {
                console.error('No features found in Map Tour feature service response.');
              }
              return fsJson.features;
            }
          }
        } catch (err) {
          console.error('Error fetching features from Map Tour feature service:', err);
        }
      }
      console.error('No features found in Map Tour layer.');
    } else if (sourceLayer) {
      for (const layer of layers) {
        const layerId = layer.id || '';
        if (layerId.includes(sourceLayer) || sourceLayer.includes(layerId)) {
          if (layer.featureCollection) {
            const fc = layer.featureCollection;
            for (const fcLayer of fc.layers || []) {
              if (fcLayer.featureSet) {
                const feats = fcLayer.featureSet.features || [];
                if (feats.length === 0) {
                  console.error('No features found in fallback featureCollection.');
                }
                return feats;
              }
            }
            console.error('No featureSet found in fallback featureCollection.');
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
                  if (fsJson.features.length === 0) {
                    console.error('No features found in fallback feature service response.');
                  }
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
      console.error('No features found in fallback layers.');
    }
    console.error('No features found in classic Map Tour data.');
    return [];
  }
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
  console.log('imageUrls:',imageUrls)
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