"""
JSON-to-JSON Classic StoryMap Converter

This module provides direct JSON-to-JSON conversion from Classic StoryMaps
(Map Tour, Map Journal, Map Series, Cascade) to ArcGIS StoryMaps without using the ArcGIS Python API.

The converters build the StoryMap JSON structure directly, which can then be uploaded
to create the new StoryMap item.
"""

import json
import os
import base64
import re
import urllib.request
import uuid
import requests
from arcgis.apps.storymap import StoryMap  # type: ignore
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup, Tag # type: ignore

from storymap_json_schema import (ALIGNMENTS, EMBEDLY_TYPES, STANDARD_THEMES,
                                  TEXT_STYLES, add_child_to_node,
                                  create_base_storymap_json, create_embed_node,
                                  create_gallery_node, create_image_node,
                                  create_image_resource, create_map_node,
                                  create_carousel_node,
                                  create_map_resource, create_separator_node,
                                  create_sidecar_structure,
                                  create_slide_structure, create_text_node,
                                  create_tour_map_geometry, create_tour_map_node,
                                  create_tour_place, create_tour_node,
                                  is_webmercator, webmercator_to_wgs84,
                                  fs_has_attachments,
                                  generate_node_id, generate_resource_id,
                                  insert_node_before_credits, set_cover_data,
                                  set_theme, validate_node_against_schema,
                                  validate_storymap_json)

# =====================================================================
# Utility Functions (reused from converter_v2.py)
# =====================================================================

def create_target_story(gis):
    """Create an empty AGSM StoryMap as a target container"""
    storymap = StoryMap(gis=gis)
    storymap_item = storymap.save(publish=True)
    target_story_id = storymap_item.id
    return target_story_id

def is_nonempty_string(string: str) -> bool:
    """Check if the string has non-whitespace content"""
    return len(string.strip()) > 0


def remove_span_tags(data):
    """Remove non-essential HTML tags from content

    Wraps content in a temporary div to ensure safe DOM manipulation
    and prevent issues with document-level nodes.
    """
    accepted_tags = ['strong', 'em', 'ol', 'li', 'ul', 'a', 'img']

    if isinstance(data, str):
        # Wrap in a container div to ensure we never manipulate document-level nodes
        wrapped_data = f'<div>{data}</div>'
        soup = BeautifulSoup(wrapped_data, 'html.parser')
        wrapper = soup.find('div')

        if not wrapper:
            return data

        # Process all tags within the wrapper (from innermost to outermost)
        for tag in reversed(wrapper.find_all()):
            if tag.name not in accepted_tags:
                tag.unwrap()

        # Return the innerHTML of the wrapper (unwrapping our temporary div)
        return ''.join(str(child) for child in wrapper.children).replace("\n", "")
    elif isinstance(data, dict):
        cleaned_data = {}
        for key, value in data.items():
            cleaned_data[key] = remove_span_tags(value)
        return cleaned_data
    elif isinstance(data, list):
        return [remove_span_tags(item) for item in data]
    else:
        return data


def determine_scale_zoom_level(given_extent, scale_coefficient=4.4):
    """Calculate zoom level from map extent"""
    from arcgis.apps.storymap import Scales # type: ignore

    max_scale = 147914382

    if given_extent is None:
        return None, None

    if 'ymax' not in given_extent or 'ymin' not in given_extent:
        return None, None

    ymax = given_extent['ymax']
    ymin = given_extent['ymin']
    map_scale = ymax - ymin
    map_scale = map_scale * scale_coefficient
    map_int_scale = map_scale
    map_zoom = None

    for scale in Scales:
        if int(map_scale) < int(scale.value['scale']):
            max_scale = scale.value['scale']
            map_int_scale = max_scale
            map_zoom = scale.value['zoom']
        else:
            map_scale = max_scale
            return map_scale, map_zoom

    return None, None


def process_img_tag(src: str, gis_token: Optional[str] = None, local_images: Optional[List] = None) -> str:
    """
    Process an image URL - download AGO resources locally

    Args:
        src: Image source URL
        gis_token: Optional authentication token for AGO resources
        local_images: Optional list to track downloaded images

    Returns:
        Local path or URL
    """
    src_url = src.replace(" ", "%20")
    image_url = src_url

    if image_url.startswith('https://www.arcgis.com/sharing/rest/content'):
        postfix = image_url.split('.')[-1]
        if gis_token:
            image_url = image_url + f'?token={gis_token}'
        media_path = f'{uuid.uuid4()}.{postfix}'
        urllib.request.urlretrieve(image_url, media_path)
        if local_images is not None:
            local_images.append(media_path)
        return media_path

    elif image_url.startswith("//www.arcgis.com/sharing/rest/content"):
        postfix = image_url.split('.')[-1]
        image_url = "https:" + image_url
        if gis_token:
            image_url = image_url + f'?token={gis_token}'
        media_path = f'{uuid.uuid4()}.{postfix}'
        urllib.request.urlretrieve(image_url, media_path)
        if local_images is not None:
            local_images.append(media_path)
        return media_path

    else:
        if src_url.startswith('https://'):
            return src_url
        else:
            return f'https:{src_url}'


def ensure_https_protocol(url: str) -> str:
    """Ensure URL has https:// protocol"""
    if url.startswith('https://'):
        return url
    elif url.startswith('//'):
        return 'https:' + url
    elif url.startswith('/'):
        return 'https://www.example.com/'
    else:
        if not url.startswith('http'):
            return 'https://' + url
        return url

def get_attr_from_list(attributes: dict, keys: list, default: str = "") -> str:
    """
    Return the first non-empty value found in attributes for the given list of keys.
    Helps in maintaining the various attributes used in different versions of Map Tours
    """
    for key in keys:
        value = attributes.get(key)
        if value is not None and str(value).strip() != "":
            return value
    return default

# =====================================================================
# StoryMap JSON Builder
# =====================================================================

class StoryMapJSONBuilder:
    """Builds StoryMap JSON structure without using the Python API"""

    def __init__(self, theme_id: str = "summit", gis_token: Optional[str] = None):
        self.theme_id = theme_id
        self.gis_token = gis_token
        self.storymap_json = create_base_storymap_json()
        self.local_images: List[str] = []

    def get_json(self) -> Dict[str, Any]:
        """Get the complete StoryMap JSON"""
        return self.storymap_json

    def add_node(self, node: Dict[str, Any], parent_id: Optional[str] = None) -> str:
        """
        Add a node to the story

        Args:
            node: Node dictionary
            parent_id: Optional parent node ID (defaults to root)

        Returns:
            Node ID
        """
        node_id = generate_node_id()
        self.storymap_json["nodes"][node_id] = node

        if parent_id:
            add_child_to_node(self.storymap_json, parent_id, node_id)
        else:
            # Add to story root before credits
            insert_node_before_credits(self.storymap_json, node_id)

        return node_id

    def create_detached_node(self, node: Dict[str, Any]) -> str:
        """
        Create a node without adding it to any parent
        Useful for sidecar media that will be added to slide children only

        Args:
            node: Node dictionary

        Returns:
            Node ID
        """
        node_id = generate_node_id()
        self.storymap_json["nodes"][node_id] = node
        return node_id

    def add_resource(self, resource: Dict[str, Any]) -> str:
        """
        Add a resource to the story

        Returns:
            Resource ID
        """
        resource_id = generate_resource_id()
        self.storymap_json["resources"][resource_id] = resource
        return resource_id

    def add_text(self, text: str, style: str = "paragraph", alignment: str = "start",
                parent_id: Optional[str] = None) -> str:
        """Add a text node"""
        node = create_text_node(text, style, alignment)
        return self.add_node(node, parent_id)

    def add_image(self, image_path: str, caption: Optional[str] = None,
                 alt: Optional[str] = None, display: str = "standard",
                 float_alignment: str = "start", parent_id: Optional[str] = None,
                 attribution: Optional[str] = None) -> str:
        """Add an image node with resource"""
        # Create resource
        resource = create_image_resource(image_path)
        resource_id = self.add_resource(resource)

        # Create node with resource_id (schema uses 'alt', not 'alt_text')
        node = create_image_node(resource_id, caption=caption, alt=alt, display=display, attribution=attribution, float_alignment=float_alignment)
        return self.add_node(node, parent_id)

    def add_map(self, map_item_id: str, extent: Optional[Dict] = None,
               viewpoint: Optional[Dict] = None, zoom: Optional[int] = None,
               map_layers: Optional[List[Dict]] = None, item_type: str = "webmap",
               parent_id: Optional[str] = None) -> Tuple[str, str]:
        """
        Add a map node with resource

        Returns:
            Tuple of (node_id, resource_id)
        """
        # Create resource
        resource = create_map_resource(map_item_id, item_type)
        resource_id = self.add_resource(resource)

        # Create node
        node = create_map_node(resource_id, extent, viewpoint, zoom, map_layers)
        node_id = self.add_node(node, parent_id)

        return node_id, resource_id

    def add_embed(self, url: str, embed_type: str = "video", display: str = "card",
                 caption: Optional[str] = None, alt: Optional[str] = None,
                 title: Optional[str] = None, description: Optional[str] = None,
                 thumbnail_url: Optional[str] = None, provider_url: Optional[str] = None,
                 parent_id: Optional[str] = None) -> str:
        """Add an embed node (no resource needed - URL goes directly in node)"""
        # NO resource creation for embeds - URL goes directly in node data per schema
        node = create_embed_node(url, embed_type, display, caption, alt,
                                title, description, thumbnail_url, provider_url)
        return self.add_node(node, parent_id)

    def add_gallery(self, image_paths: List[str], caption: Optional[str] = None,
                   alt: Optional[str] = None, layout: str = "square-dynamic",
                   parent_id: Optional[str] = None) -> str:
        """Add a gallery node with image nodes (schema requires node IDs, not resource IDs)"""
        # Create image NODES for each image (not just resources!)
        image_node_ids = []
        for image_path in image_paths:
            node_id = self.add_image(image_path)  # Creates both node + resource
            image_node_ids.append(node_id)

        # Create gallery node with image node IDs as children
        node = create_gallery_node(image_node_ids, caption, alt, layout)
        return self.add_node(node, parent_id)

    def add_separator(self, parent_id: Optional[str] = None) -> str:
        """Add a separator node"""
        node = create_separator_node()
        return self.add_node(node, parent_id)

    def add_sidecar(self, sidecar_type: str = "docked-panel") -> Tuple[str, str, str]:
        """
        Add a sidecar structure

        Returns:
            Tuple of (sidecar_id, slide_id, narrative_id)
        """
        sidecar_id, slide_id, narrative_id, nodes = create_sidecar_structure(sidecar_type)

        # Add all nodes
        self.storymap_json["nodes"].update(nodes)

        # Insert sidecar before credits
        insert_node_before_credits(self.storymap_json, sidecar_id)

        return sidecar_id, slide_id, narrative_id

    def add_slide_to_sidecar(self, sidecar_id: str, media_node_id: Optional[str] = None,
                            narrative_content_ids: Optional[List[str]] = None) -> Tuple[str, str]:
        """
        Add a slide to an existing sidecar

        Returns:
            Tuple of (slide_id, narrative_id)
        """
        slide_id, narrative_id, nodes = create_slide_structure()

        # Add narrative content
        if narrative_content_ids:
            nodes[narrative_id]["children"] = narrative_content_ids

        # Add media node as CHILD of slide (not in data.media!)
        # Structure: slide.children = [narrative_panel, media_node]
        if media_node_id:
            nodes[slide_id]["children"].append(media_node_id)

        # Add nodes
        self.storymap_json["nodes"].update(nodes)

        # Add slide to sidecar
        add_child_to_node(self.storymap_json, sidecar_id, slide_id)

        return slide_id, narrative_id

    def add_carousel(self, parent_id: Optional[str], children: List[Dict[str, Any]]) -> str:
        """Add a carousel node"""
        node = create_carousel_node(children)
        return self.add_node(node, parent_id)

    def set_cover(self, title: str, summary: str = "", by_line: str = "",
                 image_path: Optional[str] = None) -> None:
        """Set cover information"""
        image_resource_id = None

        if image_path:
            resource = create_image_resource(image_path)
            image_resource_id = self.add_resource(resource)

        set_cover_data(self.storymap_json, title, summary, by_line, image_resource_id)

    def set_theme(self, theme_id: str) -> None:
        """Set story theme"""
        self.theme_id = theme_id
        set_theme(self.storymap_json, theme_id)

    def validate(self) -> List[str]:
        """Validate the StoryMap JSON structure"""
        return validate_storymap_json(self.storymap_json)

    def get_local_images(self) -> List[str]:
        """Get list of locally downloaded images for cleanup"""
        return self.local_images


# =====================================================================
# Journal/Series JSON Converter
# =====================================================================

class JournalSeriesJSONConverter:
    """Converts MapJournal and MapSeries to StoryMap JSON"""

    def __init__(self, classic_json: Dict[str, Any], theme_id: str = "summit",
                gis_token: Optional[str] = None):
        self.classic_json = classic_json
        self.theme_id = theme_id
        self.gis_token = gis_token
        self.builder = StoryMapJSONBuilder(theme_id, gis_token)
        self.classic_type = self._detect_type()

    def _detect_type(self) -> str:
        """Detect if this is a Journal or Series"""
        # Check which field exists in the data
        story = self.classic_json.get('values', {}).get('story', {})

        if 'sections' in story:
            return "journal"
        elif 'entries' in story:
            return "series"
        else:
            # Default to journal
            return "journal"

    def convert(self) -> Dict[str, Any]:
        """
        Main conversion method

        Returns:
            StoryMap JSON structure
        """
        # Get title
        title = self.classic_json.get('values', {}).get('title', 'Untitled Story')

        # Create sidecar
        sidecar_id, initial_slide_id, initial_narrative_id = self.builder.add_sidecar("docked-panel")

        # Get sections
        if self.classic_type == 'journal':
            sections = self.classic_json.get('values', {}).get('story', {}).get('sections', [])
        else:  # series
            sections = self.classic_json.get('values', {}).get('story', {}).get('entries', [])

        # Track if we need to remove initial empty slide
        has_sections = len(sections) > 0

        # Process each section as a slide
        for section in sections:
            self._process_section(section, sidecar_id)

        # Remove initial empty slide if we added real slides
        if has_sections:
            # Remove initial slide from sidecar children
            sidecar_node = self.builder.storymap_json["nodes"][sidecar_id]
            if initial_slide_id in sidecar_node["children"]:
                sidecar_node["children"].remove(initial_slide_id)

            # Remove slide and narrative nodes
            self.builder.storymap_json["nodes"].pop(initial_slide_id, None)
            self.builder.storymap_json["nodes"].pop(initial_narrative_id, None)

        # Set cover
        self.builder.set_cover(f"(COPY) {title}")

        # Set theme
        self.builder.set_theme(self.theme_id)

        return self.builder.get_json()

    def _process_section(self, section: Dict[str, Any], sidecar_id: str) -> None:
        """Process a single section as a sidecar slide"""
        # Get media
        media_node_id = self._process_section_media(section)

        # Get narrative content
        narrative_content_ids = self._process_narrative_content(section)

        # Add slide to sidecar
        self.builder.add_slide_to_sidecar(sidecar_id, media_node_id, narrative_content_ids)

    def _process_section_media(self, section: Dict[str, Any]) -> Optional[str]:
        """Process section media (map, image, video, webpage)"""
        media = section.get('media', {})
        media_type = media.get('type')

        if media_type == 'webmap':
            return self._process_webmap_media(media)
        elif media_type == 'image':
            return self._process_image_media(media)
        elif media_type in ['video', 'webpage']:
            return self._process_embed_media(media, media_type)

        return None

    def _process_webmap_media(self, media: Dict[str, Any]) -> str:
        """Process webmap media"""
        webmap_data = media.get('webmap', {})
        map_id = webmap_data.get('id')
        extent = webmap_data.get('extent')
        layers = webmap_data.get('layers', [])

        # Calculate viewpoint
        viewpoint = None
        zoom = None
        if extent:
            scale, zoom = determine_scale_zoom_level(extent)
            if scale:
                viewpoint = {
                    "targetGeometry": extent,
                    "scale": scale
                }

        # Build layer visibility
        map_layers = None
        if layers:
            map_layers = [
                {"id": layer['id'], "visible": layer.get('visibility', True)}
                for layer in layers
            ]

        # Add map
        node_id, resource_id = self.builder.add_map(
            map_id, extent, viewpoint, zoom, map_layers, "webmap"
        )

        return node_id

    def _process_image_media(self, media: Dict[str, Any]) -> str:
        """Process image media"""
        image_data = media.get('image', {})
        url = image_data.get('url', '')
        alt = image_data.get('altText')  # Classic uses altText

        # Download if AGO resource
        processed_url = process_img_tag(url, self.gis_token, self.builder.local_images)

        # Add image (schema uses 'alt', not 'alt_text')
        node_id = self.builder.add_image(processed_url, alt=alt)

        return node_id

    def _process_embed_media(self, media: Dict[str, Any], media_type: str) -> str:
        """Process video/webpage embed media"""
        embed_data = media.get(media_type, {})
        url = embed_data.get('url', '')

        # Get iframe URL if available
        iframe = embed_data.get('frameTag')
        if iframe:
            iframe_soup = BeautifulSoup(iframe, 'html.parser')
            iframe_src = iframe_soup.find('iframe')
            if iframe_src and iframe_src.get('src'):
                url = iframe_src['src']

        # Ensure https
        url = ensure_https_protocol(url.strip("/"))

        # Determine embed type
        embedly_type = EMBEDLY_TYPES.get(media_type, 'link')

        # Extract metadata if available
        alt = embed_data.get('altText')
        title = embed_data.get('title')
        description = embed_data.get('description')
        caption = embed_data.get('caption')

        # Add embed with metadata
        node_id = self.builder.add_embed(url, embedly_type, "inline",
                                        caption=caption, alt=alt,
                                        title=title, description=description)

        return node_id

    def _process_narrative_content(self, section: Dict[str, Any]) -> List[str]:
        """Process narrative content for a section"""
        content_ids = []

        # Add title
        title = section.get('title', '')
        if title:
            title_soup = BeautifulSoup(title, 'html.parser')
            title_text = title_soup.get_text()
            if title_text.strip():
                title_id = self.builder.add_text(title_text, "h2", "start")  # Use "h2" not "heading"
                content_ids.append(title_id)

        # Get content
        if self.classic_type == 'journal':
            content = section.get('content', '')
        else:  # series
            content = section.get('description', '')

        if not content:
            return content_ids

        # Parse HTML content
        content_soup = BeautifulSoup(content, 'html.parser')

        for element in content_soup.children:
            try:
                if element.name is None:
                    continue

                node_ids = self._process_content_element(element)
                content_ids.extend(node_ids)

            except Exception as ex:
                print(f"Error processing content element: {ex}")
                continue

        return content_ids

    def _process_content_element(self, element) -> List[str]:
        """Process a single content element"""
        node_ids = []

        if not hasattr(element, 'name') or element.name is None:
            return node_ids

        # Handle images
        if element.name == 'img':
            url = element.get('src', '')
            processed_url = process_img_tag(url, self.gis_token, self.builder.local_images)
            node_id = self.builder.add_image(processed_url)
            node_ids.append(node_id)

        # Handle paragraphs
        elif element.name == 'p':
            # Check for images in paragraph
            for img in element.find_all('img'):
                url = img.get('src', '')
                processed_url = process_img_tag(url, self.gis_token, self.builder.local_images)
                node_id = self.builder.add_image(processed_url)
                node_ids.append(node_id)

            # Get text content
            text = str(element)
            if text and len(text) > 8:
                cleaned_text = remove_span_tags(text)
                p_cleaner = r'<p.*?>|</p?>'
                cleaned_text = re.sub(p_cleaner, '', cleaned_text)
                # Don't remove quotes - they're needed for HTML attributes like style="..."

                if is_nonempty_string(cleaned_text):
                    node_id = self.builder.add_text(cleaned_text, "paragraph", "start")
                    node_ids.append(node_id)

        # Handle divs
        elif element.name == 'div':
            text = str(element)
            cleaned_text = remove_span_tags(text)
            if is_nonempty_string(cleaned_text):
                node_id = self.builder.add_text(cleaned_text, "paragraph", "start")
                node_ids.append(node_id)

        # Handle elements with classes
        elif element.has_attr('class'):
            if 'caption' in element['class'] or 'image-container' in element['class']:
                # Process all direct children of the container
                # This handles cases where the container has both text and images
                for child in element.children:
                    if hasattr(child, 'name'):  # Check if it's a tag (not a string)
                        child_node_ids = self._process_content_element(child)
                        node_ids.extend(child_node_ids)

            elif 'iframe-container' in element['class']:
                iframe = element.find('iframe')
                if iframe:
                    url = iframe.get('src', '').strip("/")
                    url = ensure_https_protocol(url)

                    # Determine type
                    embedly_type = 'video' if 'mj-video-by-url' in element['class'] else 'link'
                    display = 'inline' if 'mj-video-by-url' in element['class'] else 'card'

                    # Try to extract title from iframe attributes if available
                    title = iframe.get('title')

                    node_id = self.builder.add_embed(url, embedly_type, display,
                                                    title=title)
                    node_ids.append(node_id)

        return node_ids

    def get_local_images(self) -> List[str]:
        """Get list of local images for cleanup"""
        return self.builder.get_local_images()


# =====================================================================
# Cascade JSON Converter
# =====================================================================

class CascadeJSONConverter:
    """Converts Cascade stories to StoryMap JSON"""

    def __init__(self, classic_json: Dict[str, Any], theme_id: str = "summit",
                gis_token: Optional[str] = None):
        self.classic_json = classic_json
        self.theme_id = theme_id
        self.gis_token = gis_token
        self.builder = StoryMapJSONBuilder(theme_id, gis_token)
        self._detect_theme()

    def _detect_theme(self) -> None:
        """Detect theme from cascade settings"""
        try:
            theme_value = self.classic_json['values']['settings']['theme']['colors']['themeMajor']
            theme_mapping = {
                'dark': 'obsidian',
                'light': 'summit'
            }
            self.theme_id = theme_mapping.get(theme_value, self.theme_id)
        except (KeyError, TypeError):
            pass  # Use default theme

    def convert(self) -> Dict[str, Any]:
        """
        Main conversion method

        Returns:
            StoryMap JSON structure
        """
        # Get sections
        sections = self.classic_json.get('values', {}).get('sections', [])

        if not sections:
            raise ValueError("Cascade story has no sections")

        # Process each section
        for section in sections:
            self._process_section(section)

        # Set theme
        self.builder.set_theme(self.theme_id)

        return self.builder.get_json()

    def _process_section(self, section: Dict[str, Any]) -> None:
        """Dispatch to appropriate section handler"""
        section_type = section.get('type')

        handlers = {
            'cover': self._process_cover,
            'sequence': self._process_sequence,
            'immersive': self._process_immersive,
            'title': self._process_title,
            'credits': self._process_credits,
        }

        handler = handlers.get(section_type)
        if handler:
            handler(section)

    def _process_cover(self, section: Dict[str, Any]) -> None:
        """Process cover section"""
        foreground = section.get('foreground', {})
        background = section.get('background', {})

        title = "(COPY) " + foreground.get('title', 'Untitled Story')
        subtitle = foreground.get('subtitle', '')

        # Handle cover image
        cover_media_type = background.get('type')
        image_path = None

        if cover_media_type == 'image':
            image_url = background.get('image', {}).get('url')
            if image_url:
                image_path = process_img_tag(image_url, self.gis_token, self.builder.local_images)

        # Set cover
        self.builder.set_cover(title, subtitle, "", image_path)

    def _process_sequence(self, section: Dict[str, Any]) -> None:
        """Process sequence section (narrative blocks)"""
        foreground = section.get('foreground', {})
        blocks = foreground.get('blocks', [])

        for block in blocks:
            self._process_block(block)

    def _process_immersive(self, section: Dict[str, Any]) -> None:
        """Process immersive section (floating sidecar)"""
        # Create sidecar
        sidecar_id, initial_slide_id, initial_narrative_id = self.builder.add_sidecar("floating-panel")

        views = section.get('views', [])
        title_added = False

        for view in views:
            # Process background media
            media_node_id = self._process_immersive_background(view)

            # Process foreground content
            narrative_ids = []

            # Add title (once)
            if not title_added:
                title = view.get('foreground', {}).get('title', {}).get('value', '')
                if title:
                    title_id = self.builder.add_text(title, "h2", "start")  # Use "h2" not "heading"
                    narrative_ids.append(title_id)
                    title_added = True

            # Process panels
            panels = view.get('foreground', {}).get('panels', [])
            for panel in panels:
                for block in panel.get('blocks', []):
                    node_ids = self._process_block(block, return_content_ids=True)
                    narrative_ids.extend(node_ids)

            # Add slide
            self.builder.add_slide_to_sidecar(sidecar_id, media_node_id, narrative_ids)

        # Remove initial empty slide
        if views:
            sidecar_node = self.builder.storymap_json["nodes"][sidecar_id]
            if initial_slide_id in sidecar_node["children"]:
                sidecar_node["children"].remove(initial_slide_id)
            self.builder.storymap_json["nodes"].pop(initial_slide_id, None)
            self.builder.storymap_json["nodes"].pop(initial_narrative_id, None)

    def _process_immersive_background(self, view: Dict[str, Any]) -> Optional[str]:
        """
        Process immersive view background media
        Creates DETACHED nodes (not added to story root) for sidecar media
        """
        background = view.get('background', {})
        media_type = background.get('type')

        if media_type == 'image':
            url = background.get('image', {}).get('url', '')
            processed_url = process_img_tag(url, self.gis_token, self.builder.local_images)

            # Create detached node for sidecar media
            resource = create_image_resource(processed_url)
            resource_id = self.builder.add_resource(resource)
            node = create_image_node(resource_id)
            return self.builder.create_detached_node(node)

        elif media_type in ['video', 'webpage']:
            media_data = background.get(media_type, {})
            url = media_data.get('url', '')
            url = ensure_https_protocol(url)
            embedly_type = 'video' if media_type == 'video' else 'link'

            # Extract metadata
            caption = media_data.get('caption')
            alt = media_data.get('altText')
            title = media_data.get('title')
            description = media_data.get('description')

            # Create detached node for sidecar media
            node = create_embed_node(url, embedly_type, "inline",
                                    caption, alt, title, description)
            return self.builder.create_detached_node(node)

        elif media_type == 'webmap':
            webmap_data = background.get('webmap', {})
            return self._create_detached_map_node(webmap_data, 'webmap')

        elif media_type == 'webscene':
            webscene_data = background.get('webscene', {})
            return self._create_detached_map_node(webscene_data, 'webscene')

        return None

    def _create_map_node(self, map_data: Dict[str, Any], map_type: str) -> str:
        """Create a map node from map data (adds to story root)"""
        map_id = map_data.get('id')
        extent = map_data.get('extent')
        layers = map_data.get('layers', [])

        # Calculate viewpoint for webmaps
        viewpoint = None
        zoom = None
        if extent and map_type == 'webmap':
            scale, zoom = determine_scale_zoom_level(extent)
            if scale:
                viewpoint = {
                    "targetGeometry": extent,
                    "scale": scale
                }

        # Build layer visibility
        map_layers = None
        if layers:
            map_layers = [
                {"id": layer['id'], "visible": layer.get('visibility', False)}
                for layer in layers
            ]

        node_id, resource_id = self.builder.add_map(
            map_id, extent, viewpoint, zoom, map_layers, map_type
        )

        return node_id

    def _create_detached_map_node(self, map_data: Dict[str, Any], map_type: str) -> str:
        """Create a detached map node from map data (does NOT add to story root)"""
        map_id = map_data.get('id')
        extent = map_data.get('extent')
        layers = map_data.get('layers', [])

        # Calculate viewpoint for webmaps
        viewpoint = None
        zoom = None
        if extent and map_type == 'webmap':
            scale, zoom = determine_scale_zoom_level(extent)
            if scale:
                viewpoint = {
                    "targetGeometry": extent,
                    "scale": scale
                }

        # Build layer visibility
        map_layers = None
        if layers:
            map_layers = [
                {"id": layer['id'], "visible": layer.get('visibility', False)}
                for layer in layers
            ]

        # Create resource
        resource = create_map_resource(map_id, map_type)
        resource_id = self.builder.add_resource(resource)

        # Create detached node (not added to story root)
        node = create_map_node(resource_id, extent, viewpoint, zoom, map_layers)
        node_id = self.builder.create_detached_node(node)

        return node_id

    def _process_title(self, section: Dict[str, Any]) -> None:
        """Process title section"""
        foreground = section.get('foreground', {})
        background = section.get('background', {})

        title = foreground.get('title', '')

        # Add title text
        if title:
            title_id = self.builder.add_text(title, "h1", "center")  # Use "h1" not "heading"

        # Add image if present
        if background.get('type') == 'image':
            image_url = background.get('image', {}).get('url')
            if image_url:
                image_path = process_img_tag(image_url, self.gis_token, self.builder.local_images)
                # TODO: Set as float image - requires additional node properties
                self.builder.add_image(image_path, display="float")
        else:
            # Add separator
            self.builder.add_separator()

    def _process_credits(self, section: Dict[str, Any]) -> None:
        """Process credits section (currently disabled)"""
        # Credits functionality is disabled due to API limitations
        return

    def _process_block(self, block: Dict[str, Any], return_content_ids: bool = False) -> List[str]:
        """
        Process a content block

        Args:
            block: Block dictionary
            return_content_ids: If True, return node IDs instead of adding to story

        Returns:
            List of node IDs if return_content_ids=True, else empty list
        """
        block_type = block.get('type')

        handlers = {
            'text': self._process_text_block,
            'image': self._process_image_block,
            'video': self._process_video_block,
            'webpage': self._process_webpage_block,
            'webmap': self._process_webmap_block,
            'webscene': self._process_webscene_block,
            'image-gallery': self._process_gallery_block,
        }

        handler = handlers.get(block_type)
        if handler:
            if return_content_ids:
                # Return node IDs without adding to story root
                return handler(block, parent_id=None, return_id_only=True)
            else:
                # Add to story root
                handler(block)

        return []

    def _process_text_block(self, block: Dict[str, Any], parent_id: Optional[str] = None,
                           return_id_only: bool = False) -> List[str]:
        """Process text block"""
        text_data = block.get('text', {})
        html_text = text_data.get('value', '')

        if not html_text:
            return []

        soup = BeautifulSoup(html_text, 'html.parser')
        outermost_tag = soup.find(recursive=False)

        if not outermost_tag:
            return []

        # Determine style
        tag_name = outermost_tag.name
        style = TEXT_STYLES.get(tag_name, "paragraph")

        # Determine alignment
        alignment = "center"
        if tag_name == 'p':
            style_attr = outermost_tag.get('style', '')
            if style_attr:
                align_match = re.search(r'text-align:\s*([^;]+)', style_attr)
                if align_match:
                    align_value = align_match.group(1).strip()
                    alignment = ALIGNMENTS.get(align_value, "start")
                else:
                    alignment = "start"
            else:
                alignment = "start"

        # Clean text
        # Remove color spans
        for span in outermost_tag.find_all('span'):
            if span.get('style') and 'color' in span.get('style'):
                span.unwrap()

        # Replace br with newlines
        for br in outermost_tag.find_all('br'):
            br.replace_with('\n')

        # Remove style attribute
        if outermost_tag.get('style'):
            del outermost_tag['style']

        # Normalize tags (replace b/i with strong/em) BEFORE converting to string
        for b_tag in outermost_tag.find_all('b'):
            b_tag.name = 'strong'
        for i_tag in outermost_tag.find_all('i'):
            i_tag.name = 'em'

        # Unwrap p tag
        if tag_name == 'p':
            outermost_tag.unwrap()
            text_content = str(soup)
        else:
            text_content = str(outermost_tag)

        # Don't remove quotes - they're needed for HTML attributes!

        if is_nonempty_string(text_content):
            node_id = self.builder.add_text(text_content, style, alignment, parent_id)
            return [node_id] if return_id_only else []

        return []

    def _process_image_block(self, block: Dict[str, Any], parent_id: Optional[str] = None,
                            return_id_only: bool = False) -> List[str]:
        """Process image block"""
        image_data = block.get('image', {})
        url = image_data.get('url', '')
        caption = image_data.get('caption')
        alt = image_data.get('altText')  # Classic uses altText

        if url:
            processed_url = process_img_tag(url, self.gis_token, self.builder.local_images)

            if caption:
                caption = caption.replace('"', '')

            # Schema uses 'alt', not 'alt_text'
            node_id = self.builder.add_image(processed_url, caption, alt, "standard", "start", parent_id)
            return [node_id] if return_id_only else []

        return []

    def _process_video_block(self, block: Dict[str, Any], parent_id: Optional[str] = None,
                            return_id_only: bool = False) -> List[str]:
        """Process video block"""
        video_data = block.get('video', {})
        url = video_data.get('url', '')
        caption = video_data.get('caption')
        alt = video_data.get('altText')  # Classic uses altText
        title = video_data.get('title')
        description = video_data.get('description')

        url = ensure_https_protocol(url)

        # Schema uses 'alt', not 'alt_text'
        node_id = self.builder.add_embed(url, "video", "inline", caption, alt,
                                        title, description, None, None, parent_id)
        return [node_id] if return_id_only else []

    def _process_webpage_block(self, block: Dict[str, Any], parent_id: Optional[str] = None,
                              return_id_only: bool = False) -> List[str]:
        """Process webpage block"""
        webpage_data = block.get('webpage', {})
        url = webpage_data.get('url', '')
        caption = webpage_data.get('caption')
        alt = webpage_data.get('altText')  # Classic uses altText
        title = webpage_data.get('title')
        description = webpage_data.get('description')

        url = ensure_https_protocol(url)

        # Schema uses 'alt', not 'alt_text'
        node_id = self.builder.add_embed(url, "link", "card", caption, alt,
                                        title, description, None, None, parent_id)
        return [node_id] if return_id_only else []

    def _process_webmap_block(self, block: Dict[str, Any], parent_id: Optional[str] = None,
                             return_id_only: bool = False) -> List[str]:
        """Process webmap block"""
        webmap_data = block.get('webmap', {})
        node_id = self._create_map_node(webmap_data, 'webmap')
        return [node_id] if return_id_only else []

    def _process_webscene_block(self, block: Dict[str, Any], parent_id: Optional[str] = None,
                               return_id_only: bool = False) -> List[str]:
        """Process webscene block"""
        webscene_data = block.get('webscene', {})
        node_id = self._create_map_node(webscene_data, 'webscene')
        return [node_id] if return_id_only else []

    def _process_gallery_block(self, block: Dict[str, Any], parent_id: Optional[str] = None,
                              return_id_only: bool = False) -> List[str]:
        """Process image gallery block"""
        gallery_data = block.get('image-gallery', {})
        images = gallery_data.get('images', [])
        caption = gallery_data.get('caption')
        alt = gallery_data.get('altText')  # Classic uses altText

        # Process all images
        image_paths = []
        for image in images:
            url = image.get('url', '')
            if url:
                processed_url = process_img_tag(url, self.gis_token, self.builder.local_images)
                image_paths.append(processed_url)

        if image_paths:
            # Schema uses 'alt' and requires galleryLayout
            node_id = self.builder.add_gallery(image_paths, caption, alt, "square-dynamic", parent_id)
            return [node_id] if return_id_only else []

        return []

    def get_local_images(self) -> List[str]:
        """Get list of local images for cleanup"""
        return self.builder.get_local_images()

# =====================================================================
# Map Tour JSON Converter
# =====================================================================

class MapTourJSONConverter:
    """Converts classic Map Tour stories to StoryMap JSON"""

    def __init__(self, classic_json: Dict[str, Any], theme_id: str = "summit",
                 gis_token: Optional[str] = None,
                 gis = None):
        self.classic_json = classic_json
        self.theme_id = theme_id
        self.gis_token = gis_token
        self.image_resource_map = {}
        self.gis = gis
        self.target_story_id = None
        self.builder = StoryMapJSONBuilder(theme_id, gis_token)
        self._detect_theme()

    def _detect_theme(self) -> None:
        try:
            theme_value = self.classic_json['values']['settings']['theme']['colors']['themeMajor']
            theme_mapping = {
                'dark': 'obsidian',
                'light': 'summit'
            }
            self.theme_id = theme_mapping.get(theme_value, self.theme_id)
        except (KeyError, TypeError):
            pass

    def convert(self) -> Dict[str, Any]:
        # Get title
        item_attrs = self.classic_json.get('values', {})
        title = get_attr_from_list(item_attrs, ['title',"headerLinkText"], 'Untitled MapTour')
        subtitle = item_attrs.get('subtitle', '')
        image_resource_map = self._transfer_images()
        self.image_resource_map = image_resource_map
        print("Webmap ID:", self.classic_json['values']['webmap'])

        # Get features 
        feature_set = self._get_feature_set()
        if feature_set and 'features' in feature_set:
            print(f"Number of features: {len(feature_set['features'])}")
        else:
            print("No feature set found or 'features' key missing.")
        features = feature_set.get("features", []) if feature_set else []

        # Prepare geometries and places
        geometries = {} # for tour-map node
        places = [] # for tour node

        # Create tour-map node (detached, not added to story root)
        tour_map_node = create_tour_map_node(geometries)
        tour_map_node_id = self.builder.create_detached_node(tour_map_node)

        # Create tour node (detached, not added to story root)
        tour_node = create_tour_node(
            places=[],
            map_node_id=tour_map_node_id,
            accent_color="#f9f794", # point icon color (should be derived from theme)
            narrative_panel_position="start", # start or end. unsure what the difference is. arcgis-storymaps/packages/storymaps-builder/src/blocks/immersive/README.md
            narrative_panel_size="large", # small, medium or large
            tour_type="explorer", # explorer or guided
            subtype="grid" # explorer[list or grid], guided[media or map]
        )
        tour_node_id = self.builder.create_detached_node(tour_node)

        # For each feature, create content nodes and build place dict
        for i, feature in enumerate(features):
            geom_id = str(uuid.uuid4())
            x = feature["geometry"]["x"]
            y = feature["geometry"]["y"]
            if "spatialReference" in feature["geometry"]:
                sr = feature["geometry"]["spatialReference"] # Dict: can be {"wkid": int} or {"wkt": str}
            # Convert coordinate systems if necessary
            if is_webmercator(x, y):
                long, lat = webmercator_to_wgs84(x, y)
            else:
                long, lat = x, y
            # Point geometry for tour-map node
            geom = create_tour_map_geometry(
                id=geom_id,
                long=long,
                lat=lat,
                type="POINT_NUMBERED_TOUR"
            )
            geometries[geom_id] = geom

            # Convert attributes
            attrs = feature["attributes"]
            title_text = get_attr_from_list(attrs, ["name", "NAME", "Name"])
            description_text = get_attr_from_list(attrs, ["description", "DESCRIPTION", "Description", "DESC1", "CAPTION"])
            attribution_text = get_attr_from_list(attrs, ["PHOTO_CREDIT"])

            # Place Title node (not added to story root)
            title_node = create_text_node(title_text, style="h3", alignment="start")
            title_node_id = self.builder.create_detached_node(title_node)
            # Place Description/content node(s)
            content_node = create_text_node(description_text, style="paragraph", alignment="start")
            content_node_id = self.builder.create_detached_node(content_node)
            contents = [content_node_id]

            # Place Media node (image inside a carousel)
            pic_filename = self.filenames_per_feature[i]
            resource_name = self.image_resource_map.get(pic_filename, pic_filename)
            image_node_id = self.builder.create_detached_node(create_image_node(resource_name, attribution=attribution_text))
            media_node_id = self.builder.create_detached_node(create_carousel_node([image_node_id]))

            # Place node 
            place = create_tour_place(
                id=str(uuid.uuid4()),
                feature_id=geom_id,
                contents=contents,
                media=media_node_id,
                title=title_node_id
            )
            places.append(place)

        # Update tour-map node with geometries
        self.builder.storymap_json["nodes"][tour_map_node_id]["data"]["geometries"] = geometries
        # Update the tour node's places list
        self.builder.storymap_json["nodes"][tour_node_id]["data"]["places"] = places

        # Add tour-map and tour nodes to story root (in correct order)
        story_root_id = self.builder.storymap_json["root"]
        children = self.builder.storymap_json["nodes"][story_root_id]["children"]
        # # Remove any previously added orphaned nodes (if any)
        # self.builder.storymap_json["nodes"][story_root_id]["children"] = [
        #     n for n in self.builder.storymap_json["nodes"][story_root_id]["children"]
        #     if self.builder.storymap_json["nodes"][n]["type"] not in ["tour-map", "tour", "text", "image", "carousel"]
        # ]
        # Get webmap and create resource for basemap if present
        if 'values' in self.classic_json and 'webmap' in self.classic_json['values']:
            webmap_id = self.classic_json['values']['webmap']
            tour_map_resource_id = self.builder.add_resource(create_map_resource(item_id=webmap_id))
            print(f"tour-map-id: {tour_map_resource_id} webmap: {webmap_id}")
        # If webmap resource exists, assign to basemap property
        if tour_map_resource_id:
            tour_map_node['data']['basemap'] = {
                "type": "resource",
                "value": tour_map_resource_id # Key IS NOT "resourceId"
            }
        # Insert tour-map and tour nodes
        children.extend([tour_node_id, tour_map_node_id])
        self.builder.storymap_json["nodes"][story_root_id]["children"] = children

        # Set cover and theme
        self.builder.set_cover(title=f"(CONVERSION) {title}", summary=subtitle)
        self.builder.set_theme(self.theme_id)

        return self.target_story_id, self.builder.get_json()
  
    def _get_webmap_json(self) -> Optional[Dict[str, Any]]:
        # print("Entered _get_webmap_json")
        try:
            if 'webmap_json' in self.classic_json:
                print("Found webmap_json in classic_json")
                return self.classic_json['webmap_json']
            elif 'values' in self.classic_json and 'webmap' in self.classic_json['values']:
                webmap_id = self.classic_json['values']['webmap']
                print("Fetching json from webmap item")
                webmap_item = self.gis.content.get(webmap_id)
                webmap_json = webmap_item.get_data()
                self.classic_json['webmap_json'] = webmap_json
                return webmap_json
            else:
                print("No webmap_json present")
        except Exception as ex:
            print(f"Error fetching webmap JSON: {ex}")
        return None

    def _get_feature_set(self) -> Optional[Dict[str, Any]]:
        # print("Entered _get_feature_set")
        try:
            webmap_json = self._get_webmap_json()
            if webmap_json:
                layers = webmap_json.get('operationalLayers', [])
                for layer in layers:
                    # Look for a layer with the title "Map Tour layer"
                    if layer.get('title') == "Map Tour layer":
                        print("Found Map Tour layer")
                        # Case 1: featureCollection
                        if 'featureCollection' in layer:
                            fc = layer.get('featureCollection')
                            if fc:
                                for fc_layer in fc.get('layers', []):
                                    if 'featureSet' in fc_layer:
                                        return fc_layer['featureSet']
                        # Case 2: Feature service 
                        elif 'url' in layer and layer.get('layerType') == "ArcGISFeatureLayer":
                            feature_service_url = layer['url']
                            # Query all features (may want to add where=1=1, outFields=*, etc.)
                            query_url = f"{feature_service_url}/query"
                            params = {
                                "where": "1=1",
                                "outFields": "*",
                                "f": "json"
                            }
                            response = requests.get(query_url, params=params)
                            if response.status_code == 200:
                                fs_json = response.json()
                                # Return in featureSet format
                                if "features" in fs_json:
                                    return {"features": fs_json["features"]}
                                else:
                                    print("Feature service response missing 'features' key.")
                            else:
                                print(f"Failed to fetch feature service: {feature_service_url}")
                        else:
                            print("Failed to located features")
                # If not found by title, fallback to first featureSet found
                for layer in layers:
                    fc = layer.get('featureCollection')
                    if fc:
                        for fc_layer in fc.get('layers', []):
                            if 'featureSet' in fc_layer:
                                return fc_layer['featureSet']
            # Fallback: look for featureSet directly
            if 'featureSet' in self.classic_json:
                return self.classic_json['featureSet']
        except Exception as ex:
            print(f"Error in _get_feature_set: {ex}")
        return None
    
    def _transfer_images(self) -> Dict[str, str]:
        """
        Fetch externally hosted images and upload them to AGO resources (in memory).
        Avoid uploading duplicate images; reuse resource for repeated references.
        Returns a dict mapping filenames to resource names.
        """
        if not self.target_story_id:
            self.target_story_id = create_target_story(self.gis)
        image_resource_map = {}
        feature_set = self._get_feature_set()
        if not feature_set or "features" not in feature_set:
            self.filenames_per_feature = []
            return image_resource_map

        add_resource_url = f"https://www.arcgis.com/sharing/rest/content/users/{self.gis.properties.user.username}/items/{self.target_story_id}/addResources"
        token = self.gis._con.token if self.gis else None

        # Get feature service URL if present
        webmap_json = self._get_webmap_json()
        feature_service_url = None
        if webmap_json:
            for layer in webmap_json.get('operationalLayers', []):
                if layer.get('title') == "Map Tour layer" and 'url' in layer:
                    feature_service_url = layer['url']

        # Track seen images by URL or attachment ID
        seen_images = {}  # key: img_url or (feature_service_url, objectid, att_id) -> (filename, resource_id)
        filenames_per_feature = []

        for i, feature in enumerate(feature_set["features"]):
            attrs = feature.get("attributes", {})
            objectid = attrs.get("objectid") or attrs.get("OBJECTID")
            # Try both lowercase and uppercase keys
            attrs = feature["attributes"]
            img_url = get_attr_from_list(attrs, ["url", "URL", "pic_url", "PIC_URL"])

            # Case 1: image from URL
            if img_url:
                if img_url in seen_images:
                    filename, resource_id = seen_images[img_url]
                else:
                    uid = base64.urlsafe_b64encode(os.urandom(4)).decode()[:6]
                    filename = f"place_{i+1:03d}_{uid}.jpg"
                    try:
                        response = requests.get(img_url, timeout=10)
                        if response.status_code == 200:
                            files = {"file": (filename, response.content)}
                            params = {
                                "f": "json",
                                "token": token,
                                "fileName": filename
                            }
                            upload_response = requests.post(add_resource_url, files=files, data=params)
                            if upload_response.status_code == 200 and upload_response.json().get("success"):
                                resource = create_image_resource(filename)
                                resource_id = self.builder.add_resource(resource)
                                print(f"Uploaded resource: {filename}")
                            else:
                                print(f"Failed to upload resource: {filename}. Response: {upload_response.text}")
                                resource_id = filename  # fallback
                        else:
                            print(f"Failed to fetch image: {img_url}")
                            resource_id = filename  # fallback
                    except Exception as e:
                        print(f"Error fetching/uploading image {img_url}: {e}")
                        resource_id = filename  # fallback
                    seen_images[img_url] = (filename, resource_id)
                filenames_per_feature.append(filename)
                image_resource_map[filename] = resource_id
            # Case 2: Feature service attachments
            elif feature_service_url and objectid:
                # Get attachment info
                attachments_url = f"{feature_service_url}/{objectid}/attachments?f=json"
                if token:
                    attachments_url += f"&token={token}"
                try:
                    att_response = requests.get(attachments_url)
                    if att_response.status_code == 200:
                        att_json = att_response.json()
                        found_valid = False
                        for att in att_json.get("attachmentInfos", []):
                            att_id = att["id"]
                            att_content_type = att.get("contentType", "")
                            # Only process valid image types
                            if att_content_type not in ["image/jpeg", "image/png", "image/gif"]:
                                print(f"Skipping attachment {att['name']} (unsupported type: {att_content_type})")
                                continue
                            att_key = (feature_service_url, objectid, att_id)
                            if att_key in seen_images:
                                filename, resource_id = seen_images[att_key]
                            else:
                                uid = base64.urlsafe_b64encode(os.urandom(4)).decode()[:6]
                                filename = f"place_{i+1:03d}_{uid}.jpg"
                                att_download_url = f"{feature_service_url}/{objectid}/attachments/{att_id}?token={token}"
                                att_file_response = requests.get(att_download_url, stream=True)
                                if att_file_response.status_code == 200:
                                    files = {"file": (filename, att_file_response.content)}
                                    params = {
                                        "f": "json",
                                        "token": token,
                                        "fileName": filename
                                    }
                                    upload_response = requests.post(add_resource_url, files=files, data=params)
                                    if upload_response.status_code == 200 and upload_response.json().get("success"):
                                        resource = create_image_resource(filename)
                                        resource_id = self.builder.add_resource(resource)
                                        print(f"Uploaded attachment: {filename}")
                                    else:
                                        print(f"Failed to upload attachment: {filename}. Response: {upload_response.text}")
                                        resource_id = filename  # fallback
                                else:
                                    print(f"Failed to download attachment: {att_download_url}")
                                    resource_id = filename  # fallback
                                seen_images[att_key] = (filename, resource_id)
                            filenames_per_feature.append(filename)
                            image_resource_map[filename] = resource_id
                            found_valid = True
                            break  # Only use first valid image attachment per feature
                        if not found_valid:
                            filenames_per_feature.append("")  # No valid image
                    else:
                        print(f"Failed to fetch attachments for objectid {objectid}")
                        filenames_per_feature.append("")
                except Exception as e:
                    print(f"Error fetching/uploading attachment for objectid {objectid}: {e}")
                    filenames_per_feature.append("")
            else:
                filenames_per_feature.append("")  # No image for this feature

        self.filenames_per_feature = filenames_per_feature
        return image_resource_map

# =====================================================================
# Converter Factory
# =====================================================================

class JSONConverterFactory:
    """Factory for creating appropriate JSON converters"""

    @staticmethod
    def get_converter(classic_json: Dict[str, Any], theme_id: str = "summit",
                     gis_token: Optional[str] = None, gis=None):
        """
        Get appropriate converter based on classic story type

        Args:
            classic_json: Classic story JSON data
            theme_id: Theme to apply
            gis_token: Optional GIS authentication token
            gis: Optional authenticated GIS object

        Returns:
            Appropriate converter instance
        """
        # Detect type from data structure
        values = classic_json.get('values', {})

        # Check for Map Tour
        if 'template' in values and values['template'] == 'Map Tour':
            return MapTourJSONConverter(classic_json, theme_id, gis_token, gis=gis)
       
        # Check for Journal/Series
        if 'story' in values:
            story = values['story']
            if 'sections' in story or 'entries' in story:
                return JournalSeriesJSONConverter(classic_json, theme_id, gis_token)

        # Check for Cascade
        if 'sections' in values:
            # Cascade has sections directly in values
            return CascadeJSONConverter(classic_json, theme_id, gis_token)

        raise ValueError("Unknown classic story type")

# =====================================================================
# Main Conversion Functions
# =====================================================================

def convert_classic_to_json(classic_json: Dict[str, Any], theme_id: str = "summit",
                           gis_token: Optional[str] = None, gis = None) -> Tuple[str, Dict[str, Any]]:
    """
    Convert classic story JSON to StoryMap JSON

    Args:
        classic_json: Classic story data
        theme_id: Theme to apply
        gis_token: Optional GIS token for downloading images

    Returns:
        StoryMap JSON structure
    """
    converter = JSONConverterFactory.get_converter(classic_json, theme_id, gis_token, gis=gis)
    result = converter.convert()

    # Unpack tuple if MapTourJSONConverter, else just JSON
    if isinstance(result, tuple) and len(result) == 2:
        target_story_id, storymap_json = result
    else:
        target_story_id, storymap_json = None, result

    # Validate
    errors = validate_storymap_json(storymap_json)
    if errors:
        print("Warning: JSON validation errors:")
        for error in errors:
            print(f"  - {error}")

    return target_story_id,storymap_json


def save_json_to_file(storymap_json: Dict[str, Any], output_path: str) -> None:
    """
    Save StoryMap JSON to file

    Args:
        storymap_json: StoryMap JSON structure
        output_path: Output file path
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(storymap_json, f, indent=2, ensure_ascii=False)

    print(f"Saved StoryMap JSON to: {output_path}")


def cleanup_local_images(converter) -> None:
    """
    Clean up locally downloaded images

    Args:
        converter: Converter instance with get_local_images() method
    """
    local_images = converter.get_local_images()

    for image_path in local_images:
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
        except Exception as e:
            print(f"Warning: Could not delete {image_path}: {e}")


# Example usage
if __name__ == "__main__":
    # Example: Convert a classic story
    # You would load the classic story JSON and pass it to the converter

    # Load classic story data
    # with open('classic_story.json', 'r') as f:
    #     classic_json = json.load(f)

    # Convert to StoryMap JSON
    # storymap_json = convert_classic_to_json(classic_json, theme_id="summit")

    # Save to file
    # save_json_to_file(storymap_json, 'new_storymap.json')

    print("JSON converter module loaded successfully")
    print("Use convert_classic_to_json() to convert classic stories to StoryMap JSON")

