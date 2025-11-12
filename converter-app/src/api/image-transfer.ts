/**
 * Image Transfer Utilities
 * Handle downloading images from classic story and uploading to new story
 */

import { addResource } from './arcgis-client';

/**
 * Check if URL is an ArcGIS Online resource
 */
export function isAgoResource(url: string): boolean {
    return (
        url.includes('www.arcgis.com/sharing/rest/content') ||
        url.includes('//www.arcgis.com/sharing/rest/content')
    );
}

/**
 * Extract classic item ID from AGO resource URL
 */
export function extractItemIdFromUrl(url: string): string | null {
    const match = url.match(/\/items\/([a-f0-9]+)\/resources/i);
    return match ? match[1] : null;
}

/**
 * Extract resource filename from URL
 */
export function extractResourceName(url: string): string {
    // Get the part after /resources/
    const parts = url.split('/resources/');
    if (parts.length > 1) {
        // Remove query params
        const filename = parts[1].split('?')[0];
        return decodeURIComponent(filename);
    }
    // Fallback: use last part of path
    const lastPart = url.split('/').pop()?.split('?')[0];
    return lastPart || 'image.jpg';
}

/**
 * Generate a unique resource name for the new story
 */
export function generateResourceName(originalName: string): string {
    const extension = originalName.split('.').pop() || 'jpg';
    const uuid = Math.random().toString(36).substring(2, 15);
    return `${uuid}.${extension}`;
}

/**
 * Fetch image from AGO resource and convert to Blob
 */
export async function fetchImageAsBlob(url: string, token: string): Promise<Blob> {
    // Ensure URL has https protocol
    let fullUrl = url;
    if (url.startsWith('//')) {
        fullUrl = 'https:' + url;
    } else if (!url.startsWith('http')) {
        fullUrl = 'https://' + url;
    }

    // Add token to URL
    const separator = fullUrl.includes('?') ? '&' : '?';
    const urlWithToken = `${fullUrl}${separator}token=${token}`;

    const response = await fetch(urlWithToken);
    if (!response.ok) {
        throw new Error(`Failed to fetch image: ${response.statusText}`);
    }

    return response.blob();
}

/**
 * Result of image transfer
 */
export interface ImageTransferResult {
    originalUrl: string;
    resourceName: string;  // Just the filename
    isTransferred: boolean;
}

/**
 * Transfer image from classic story to new story
 * Downloads from classic resources and uploads to target resources
 * Returns the resource NAME (filename), not full URL
 */
export async function transferImage(
    imageUrl: string,
    targetItemId: string,
    username: string,
    token: string,
    filename?: string
): Promise<{ originalUrl: string; resourceName: string; isTransferred: boolean }> {
  try {
    console.log('[transferImage] Starting transfer:', { imageUrl, filename, targetItemId });
    let blob: Blob;
    let originalName: string;

    if (isAgoResource(imageUrl)) {
      // AGO resource: fetch with token
      blob = await fetchImageAsBlob(imageUrl, token);
      originalName = extractResourceName(imageUrl);
    } else {
      // External image: try direct fetch first
      try {
        const response = await fetch(imageUrl);
        if (!response.ok) throw new Error(`Failed to fetch external image: ${response.statusText}`);
        blob = await response.blob();
        originalName = extractResourceName(imageUrl);
      } catch (err) {
        // Fallback to proxy if direct fetch fails (likely CORS)
        console.warn('[transferImage] Direct fetch failed, trying proxy:', { imageUrl, error: err });
        blob = await fetchImageWithProxy(imageUrl);
        originalName = extractResourceName(imageUrl);
      }
    }

    // Generate a new resource name for AGO
    const newResourceName = filename || generateResourceName(originalName);
    // Upload to AGO story item
    console.log('[transferImage] Uploading to AGO:', { newResourceName, blob });
    await addResource(targetItemId, username, blob, newResourceName, token);

    console.log('[transferImage] Transfer successful:', { imageUrl, newResourceName });    
    return {
      originalUrl: imageUrl,
      resourceName: newResourceName,
      isTransferred: true
    };
  } catch (error) {
    console.error('[transferImage] Transfer failed:', { imageUrl, error });
    return {
      originalUrl: imageUrl,
      resourceName: imageUrl,
      isTransferred: false
    };
  }
}

/**
 * Transfer multiple images (batch processing with progress)
 */
// export async function transferImages(
//     imageUrls: string[],
//     targetItemId: string,
//     username: string,
//     token: string,
//     onProgress?: (current: number, total: number, message: string) => void
// ): Promise<ImageTransferResult[]> {
//     const results: ImageTransferResult[] = [];

//     for (let i = 0; i < imageUrls.length; i++) {
//         const originalUrl = imageUrls[i];

//         if (onProgress) {
//             onProgress(i + 1, imageUrls.length, `Processing image ${i + 1} of ${imageUrls.length}`);
//         }

//         const result = await transferImage(
//             originalUrl,
//             targetItemId,
//             username,
//             token,
//             onProgress ? (msg) => onProgress(i + 1, imageUrls.length, msg) : undefined
//         );

//         results.push(result);
//     }

//     return results;
// }

/**
 * Transfer multiple images (batch processing with progress)
 */
export async function transferImages(
  imageUrls: string[],
  targetItemId: string,
  username: string,
  token: string,
  onProgress?: (current: number, total: number, msg: string) => void
): Promise<{ originalUrl: string; resourceName: string; isTransferred: boolean }[]> {
  console.log('[transferImages] Starting batch transfer:', { imageUrls, targetItemId });  
  const results: { originalUrl: string; resourceName: string; isTransferred: boolean }[] = [];
  for (let i = 0; i < imageUrls.length; i++) {
    const imageUrl = imageUrls[i];
    if (onProgress) {
      onProgress(i + 1, imageUrls.length, `Transferring image ${i + 1} of ${imageUrls.length}`);
    }
    const result = await transferImage(imageUrl, targetItemId, username, token);
    results.push(result);
  }
  return results;
}

/**
 * Fetch an image using a local proxy server to avoid CORS errors
 */
async function fetchImageWithProxy(imageUrl: string): Promise<Blob> {
  const proxyUrl = `http://localhost:3001/proxy-image?url=${encodeURIComponent(imageUrl)}`;
  const response = await fetch(proxyUrl);
  if (!response.ok) throw new Error('Failed to fetch image via proxy');
  return await response.blob();
}

/**
 * Scan StoryMap JSON for all image URLs that need to be transferred
 * * Updated to scan for both 'url' and 'src' properties
 */
export function collectImageUrls(storymapJson: any): string[] {
    const imageUrls = new Set<string>();

    // Scan resources for image URLs
    if (storymapJson.resources) {
        for (const resource of Object.values<any>(storymapJson.resources)) {
            if (resource.type === 'image') {
                const url = resource.data?.url || resource.data?.src;
                if (url) { 
                    imageUrls.add(url);
                }
            }
        }
    }

    return Array.from(imageUrls);
}

/**
 * Update StoryMap JSON to fix image resource structures
 * For transferred images: use resourceId + provider: "item-resource"
 * For external images: use src + provider: "uri"
 */
export function updateImageUrlsInJson(storymapJson: any, transferResults: Record<string, string>) {
  // Normalize urls
  const normalizeUrl = (url: string) => decodeURIComponent(url);  
    // For each image resource, if its src matches a transferred URL, update it
    if (storymapJson.resources) {
        for (const [resourceId, resource] of Object.entries<any>(storymapJson.resources)) {
            if (resource.type === "image" && resource.data?.src) {
                const originalUrl = resource.data.src;
                // Try to match with normalized URLs
                const matchKey = Object.keys(transferResults).find(
                    k => normalizeUrl(k) === normalizeUrl(originalUrl)
                );
                if (matchKey) {
                    // Change 'src' to 'resourceId' and set provider to 'item-resource'
                    resource.data.resourceId = transferResults[matchKey];
                    delete resource.data.src;
                    resource.data.provider = "item-resource";
                } else {
                    console.log(`No match for resource ${resourceId}: ${originalUrl}`);
                }
            }
        }
    }
    return storymapJson;
}

// export function updateImageUrlsInJson(
//     storymapJson: any,
//     transferResults: ImageTransferResult[]
// ): any {
//     const updated = JSON.parse(JSON.stringify(storymapJson));

//     // Create lookup map
//     const resultMap = new Map<string, ImageTransferResult>();
//     for (const result of transferResults) {
//         resultMap.set(result.originalUrl, result);
//     }

//     // Update resources
//     if (updated.resources) {
//         for (const resource of Object.values<any>(updated.resources)) {
//             if (resource.type === 'image' && resource.data?.url) {
//                 const oldUrl = resource.data.url;
//                 const result = resultMap.get(oldUrl);

//                 if (result && result.isTransferred) {
//                     // Image was transferred - use resourceId structure
//                     delete resource.data.url;
//                     delete resource.data.type;
//                     resource.data.resourceId = result.resourceName;
//                     resource.data.provider = 'item-resource';
//                     resource.data.height = 1024;
//                     resource.data.width = 1024;
//                 } else {
//                     // External URL or transfer failed - use src structure
//                     const url = result ? result.resourceName : oldUrl;
//                     delete resource.data.url;
//                     delete resource.data.type;
//                     resource.data.src = url;
//                     resource.data.provider = 'uri';
//                     resource.data.height = 1024;
//                     resource.data.width = 1024;
//                 }
//             }
//         }
//     }

//     return updated;
// }

