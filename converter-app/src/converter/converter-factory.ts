/**
 * Converter Factory
 * Selects appropriate converter based on classic story type
 * Ported from JSONConverterFactory in converter_json.py
 */

import type { ClassicStoryMapJSON } from '../types/storymap';
import { JournalSeriesConverter } from './journal-converter';
import { CascadeConverter } from './cascade-converter';
import { MapTourConverter } from './maptour-converter';
import { collectImageUrls, transferImages, updateImageUrlsInJson } from '../api/image-transfer';

export class ConverterFactory {
  /**
   * Get appropriate converter based on classic story type
   */
  static getConverter(
    classicJson: ClassicStoryMapJSON,
    themeId: string = 'summit'
  ): JournalSeriesConverter | CascadeConverter | MapTourConverter {
    const values = classicJson.values;

    if (!values) {
      throw new Error('Invalid classic story JSON: missing "values" key');
    }

    // Check for Map Tour
  let rawTemplate = (values as any).template || (values as any).templateName || (values as any).name || '';
  if (typeof rawTemplate !== 'string') rawTemplate = String(rawTemplate);
  const template = rawTemplate.toLowerCase();
    if (template.includes('map tour')) {
        return new MapTourConverter(classicJson, themeId);
    }

    // Check for Journal/Series
    if (values.story) {
      const story = values.story;
      if (story.sections || story.entries) {
        return new JournalSeriesConverter(classicJson, themeId);
      }
    }

    // Check for Cascade
    if (values.sections) {
      // Cascade has sections directly in values
      return new CascadeConverter(classicJson, themeId);
    }

    throw new Error('Unknown classic story type');
  }
}

/**
 * Main conversion function
 */
export async function convertClassicToJson(
  classicJson: ClassicStoryMapJSON,
  themeId: string = 'summit',
  username: string,
  token: string,
  targetStoryId: string
): Promise<any> {
  const converter = ConverterFactory.getConverter(classicJson, themeId, username, token);
  let storymapJson = await converter.convert();

  // 1. Collect image URLs before any update
  const imageUrls = collectImageUrls(storymapJson);

  // 2. Transfer images and get mapping
  const transferResultsArray = await transferImages(
    imageUrls,
    targetStoryId,
    username,
    token
  );
  const transferResults: Record<string, string> = {};
  for (const result of transferResultsArray) {
    transferResults[result.originalUrl] = result.resourceName;
  }

  // 3. Update resources in JSON
  storymapJson = updateImageUrlsInJson(storymapJson, transferResults);

  return storymapJson;
}

