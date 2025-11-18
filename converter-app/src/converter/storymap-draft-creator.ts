/* eslint-disable @typescript-eslint/no-explicit-any */

/**
 * Empty StoryMap Creator
 * Uses the ArcGIS REST API to create a draft story
 * to be used as the container for the conversion
 */
import { createBaseStorymapJson } from "./storymap-schema";

export async function createDraftStoryMap(username: string, token: string, title: string) {
  const timestamp = Date.now();
  const draftResourceName = `draft_${timestamp}.json`;
  const typeKeywords = [
    "StoryMap",
    `smdraftresourceid:${draftResourceName}`,
    "smstatusdraft",
    "smeditorapp:converter-v3alpha"
  ];

  // Generate minimal valid StoryMap JSON
  const minimalStoryMapJson = createBaseStorymapJson();  

  const params = new URLSearchParams({
    f: "json",
    type: "StoryMap",
    title,
    text: JSON.stringify(minimalStoryMapJson),
    typeKeywords: typeKeywords.join(","),
    token,
  });

  const response = await fetch(
    `https://www.arcgis.com/sharing/rest/content/users/${username}/addItem`,
    {
      method: "POST",
      body: params,
    }
  );
  const data = await response.json();
  if (!data.success) throw new Error(data.error?.message || "Failed to create StoryMap");
  return data.id;
}

/**
 * Create a custom StoryMap Theme from classic JSON theme values
 */
export async function createDerivedTheme(
  username: string,
  token: string,
  classicJson: any,
  fallbackBaseTheme: string = 'summit'
): Promise<string> {
  const classicTheme = classicJson?.values?.settings?.theme || {};
  const colors = classicTheme.colors || {};
  const fonts = classicTheme.fonts || {};

  // Derive theme title from classic story title
  const rawTitle = classicJson?.values?.title || 'Untitled Story';
  const cleanedTitle = String(rawTitle).replace(/\s+/g, ' ').trim();
  const themeTitle = `${cleanedTitle} Theme`;

  // Base theme selection
  const baseThemeId = (colors.themeMajor || '').toLowerCase() === 'black'
    ? 'obsidian'
    : (colors.themeMajor || '').toLowerCase() === 'dark'
      ? 'obsidian'
      : (colors.themeMajor || '').toLowerCase() === 'white'
        ? 'summit'
        : fallbackBaseTheme;

  // Font id extraction (strip font-family wrapper)
  function extractFontId(fontObj: any, fallback: string): string {
    if (!fontObj || !fontObj.id) return fallback;
    return fontObj.id; // Classic already stores a short id
  }

  const titleFontId = extractFontId(fonts.sectionTitle, 'notoSans');
  const bodyFontId = extractFontId(fonts.sectionContent, 'notoSans');

  // Build variables object
  const variables: Record<string, any> = {
    baseThemeId,
    headerFooterBackgroundColor: colors.panel || '#ffffff',
    backgroundColor: colors.panel || '#ffffff',
    titleFontId,
    titleColor: colors.text || '#000000',
    titleColorDark: colors.text || '#000000',
    titleColorLight: '#ffffff',
    bodyFontId,
    bodyColor: colors.text || '#000000',
    bodyColorDark: colors.text || '#000000',
    bodyColorLight: '#ffffff',
    bodyMutedColor: colors.softText || '#666666',
    themeColor1: colors.softBtn || colors.textLink || '#0079c1',
    themeColor2: colors.textLink || '#555555',
    themeColor3: colors.dotNav || '#444444',
    borderRadius: 0,
    shape: 'square'
  };

  const themePayload = {
    title: themeTitle,
    baseThemeId,
    isFromOrgTheme: false,
    variables,
    resources: {}
  };

  const params = new URLSearchParams({
    f: 'json',
    type: 'StoryMap Theme',
    title: themeTitle,
    text: JSON.stringify(themePayload),
    token
  });

  const response = await fetch(
    `https://www.arcgis.com/sharing/rest/content/users/${username}/addItem`,
    { method: 'POST', body: params }
  );
  const data = await response.json();
  if (!data.success) {
    throw new Error(data.error?.message || 'Failed to create theme');
  }
  return data.id; // theme item id
}

/**
 * Parse classic theme colors/fonts into a normalized object (if needed separately)
 */
export function parseClassicTheme(classicJson: any): Record<string, any> {
  const theme = classicJson?.values?.settings?.theme || {};
  const colors = theme.colors || {};
  const fonts = theme.fonts || {};
  return {
    themeMajor: colors.themeMajor,
    panel: colors.panel,
    text: colors.text,
    textLink: colors.textLink,
    softText: colors.softText,
    softBtn: colors.softBtn,
    dotNav: colors.dotNav,
    titleFontId: fonts.sectionTitle?.id,
    bodyFontId: fonts.sectionContent?.id
  };
}