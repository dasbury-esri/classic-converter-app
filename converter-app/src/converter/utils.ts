/**
 * Utility functions for StoryMap conversion
 * Ported from converter_json.py
 */

import type { Extent } from '../types/storymap';

/**
 * Check if a string has non-whitespace content
 */
export function isNonEmptyString(str: string): boolean {
  return str.trim().length > 0;
}

/**
 * Remove non-essential HTML tags from content
 * Preserves: strong, em, ol, li, ul, a, img
 */
export function removeSpanTags(data: any): any {
  const acceptedTags = ['strong', 'em', 'ol', 'li', 'ul', 'a', 'img'];

  if (typeof data === 'string') {
    // Wrap in a container div to ensure we never manipulate document-level nodes
    const wrappedData = `<div>${data}</div>`;
    const parser = new DOMParser();
    const doc = parser.parseFromString(wrappedData, 'text/html');

    // Get the wrapper div we created
    const wrapper = doc.body.firstElementChild;
    if (!wrapper) {
      return data;
    }

    // Convert NodeList to array and process in reverse order (innermost to outermost)
    // This avoids issues with manipulating the DOM while iterating
    const allTags = Array.from(wrapper.querySelectorAll('*'));

    // Process from innermost to outermost (reverse order)
    for (let i = allTags.length - 1; i >= 0; i--) {
      const tag = allTags[i];
      if (!acceptedTags.includes(tag.tagName.toLowerCase())) {
        // Unwrap - replace tag with its contents
        const parent = tag.parentNode;
        if (parent) {
          // Move all children before the tag
          while (tag.firstChild) {
            parent.insertBefore(tag.firstChild, tag);
          }
          // Remove the now-empty tag
          parent.removeChild(tag);
        }
      }
    }

    // Return the innerHTML of the wrapper (unwrapping our temporary div)
    return wrapper.innerHTML.replace(/\n/g, '');
  } else if (typeof data === 'object' && data !== null) {
    if (Array.isArray(data)) {
      return data.map(item => removeSpanTags(item));
    } else {
      const cleaned: Record<string, any> = {};
      for (const [key, value] of Object.entries(data)) {
        cleaned[key] = removeSpanTags(value);
      }
      return cleaned;
    }
  }

  return data;
}

/**
 * Scale/zoom mappings from ArcGIS Python API
 * Based on Web Mercator projection
 */
const SCALE_ZOOM_LEVELS = [
  { scale: 591657527, zoom: 0 },
  { scale: 295828763, zoom: 1 },
  { scale: 147914381, zoom: 2 },
  { scale: 73957190, zoom: 3 },
  { scale: 36978595, zoom: 4 },
  { scale: 18489297, zoom: 5 },
  { scale: 9244648, zoom: 6 },
  { scale: 4622324, zoom: 7 },
  { scale: 2311162, zoom: 8 },
  { scale: 1155581, zoom: 9 },
  { scale: 577790, zoom: 10 },
  { scale: 288895, zoom: 11 },
  { scale: 144447, zoom: 12 },
  { scale: 72223, zoom: 13 },
  { scale: 36111, zoom: 14 },
  { scale: 18055, zoom: 15 },
  { scale: 9027, zoom: 16 },
  { scale: 4513, zoom: 17 },
  { scale: 2256, zoom: 18 },
  { scale: 1128, zoom: 19 },
  { scale: 564, zoom: 20 },
  { scale: 282, zoom: 21 },
  { scale: 141, zoom: 22 },
  { scale: 70, zoom: 23 }
];

/**
 * Calculate zoom level from map extent
 * Ported from determine_scale_zoom_level()
 */
export function determineScaleZoomLevel(
  extent: Extent | null | undefined,
  scaleCoefficient: number = 4.4
): { scale: number; zoom: number } | null {
  if (!extent || !extent.ymax || !extent.ymin) {
    return null;
  }

  const ymax = extent.ymax;
  const ymin = extent.ymin;
  let mapScale = (ymax - ymin) * scaleCoefficient;

  let selectedScale = SCALE_ZOOM_LEVELS[0].scale;
  let selectedZoom = SCALE_ZOOM_LEVELS[0].zoom;

  for (const level of SCALE_ZOOM_LEVELS) {
    if (mapScale < level.scale) {
      selectedScale = level.scale;
      selectedZoom = level.zoom;
    } else {
      return { scale: selectedScale, zoom: selectedZoom };
    }
  }

  return { scale: selectedScale, zoom: selectedZoom };
}

/**
 * Ensure URL has https:// protocol
 */
export function ensureHttpsProtocol(url: string): string {
  if (url.startsWith('https://')) {
    return url;
  } else if (url.startsWith('//')) {
    return 'https:' + url;
  } else if (url.startsWith('/')) {
    return 'https://www.example.com/';
  } else {
    if (!url.startsWith('http')) {
      return 'https://' + url;
    }
    return url;
  }
}

/**
 * Generate a unique node ID
 */
export function generateNodeId(): string {
  // Generate random 6-character hex string like Python uuid.uuid4().hex[:6]
  return 'n-' + Math.random().toString(36).substring(2, 8);
}

/**
 * Generate a unique resource ID
 */
export function generateResourceId(): string {
  return 'r-' + Math.random().toString(36).substring(2, 8);
}

/**
 * Generate a UUID for Map Tour geometries
 */
export function generateUUID(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    // Modern browsers and Node.js v16.17+
    return crypto.randomUUID();
  }
  // Fallback for older environments
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

/**
 * Helper to allow a flexible list of attributes from different classic versions
 */
export function getAttrFromList(attrs: Record<string, any>, keys: string[], fallback: string = ''): string {
  for (const key of keys) {
    if (attrs[key] !== undefined && attrs[key] !== null && String(attrs[key]).trim() !== '') {
      return String(attrs[key]).trim();
    }
  }
  return fallback;
}

/**
 * Parse HTML and extract text content
 */
export function parseHtmlText(html: string): string {
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, 'text/html');
  return doc.body.textContent || '';
}

/**
 * Extract provider domain from URL for embed metadata
 */
export function extractProviderUrl(url: string): string {
  try {
    const urlObj = new URL(url);
    return `${urlObj.protocol}//${urlObj.hostname}`;
  } catch {
    return '';
  }
}

/**
 * Use the browser to save JSON files for debugging
 */
export function saveJsonToFile(obj: any, filename: string) {
  const blob = new Blob([JSON.stringify(obj, null, 4)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}