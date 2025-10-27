"""
JSON-to-JSON Classic StoryMap Converter

This module provides direct JSON-to-JSON conversion from Classic StoryMaps
(MapJournal, MapSeries, Cascade) to ArcGIS StoryMaps without using the ArcGIS Python API.

The converters build the StoryMap JSON structure directly, which can then be uploaded
to create the new StoryMap item.
"""

import json
import os
import re
import urllib.request
import uuid
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup, Tag

from storymap_json_schema import (ALIGNMENTS, EMBEDLY_TYPES, STANDARD_THEMES,
                                  TEXT_STYLES, add_child_to_node,
                                  create_base_storymap_json, create_embed_node,
                                  create_gallery_node, create_image_node,
                                  create_image_resource, create_map_node,
                                  create_map_resource, create_separator_node,
                                  create_sidecar_structure,
                                  create_slide_structure, create_text_node,
                                  generate_node_id, generate_resource_id,
                                  insert_node_before_credits, set_cover_data,
                                  set_theme, validate_node_against_schema,
                                  validate_storymap_json)

# =====================================================================
# Utility Functions (reused from converter_v2.py)
# =====================================================================

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
    from arcgis.apps.storymap import Scales

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
                 float_alignment: str = "start", parent_id: Optional[str] = None) -> str:
        """Add an image node with resource"""
        # Create resource
        resource = create_image_resource(image_path)
        resource_id = self.add_resource(resource)

        # Create node with resource_id (schema uses 'alt', not 'alt_text')
        node = create_image_node(resource_id, caption, alt, display, float_alignment)
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
# Converter Factory
# =====================================================================

class JSONConverterFactory:
    """Factory for creating appropriate JSON converters"""

    @staticmethod
    def get_converter(classic_json: Dict[str, Any], theme_id: str = "summit",
                     gis_token: Optional[str] = None):
        """
        Get appropriate converter based on classic story type

        Args:
            classic_json: Classic story JSON data
            theme_id: Theme to apply
            gis_token: Optional GIS authentication token

        Returns:
            Appropriate converter instance
        """
        # Detect type from data structure
        values = classic_json.get('values', {})

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
                           gis_token: Optional[str] = None) -> Dict[str, Any]:
    """
    Convert classic story JSON to StoryMap JSON

    Args:
        classic_json: Classic story data
        theme_id: Theme to apply
        gis_token: Optional GIS token for downloading images

    Returns:
        StoryMap JSON structure
    """
    converter = JSONConverterFactory.get_converter(classic_json, theme_id, gis_token)
    storymap_json = converter.convert()

    # Validate
    errors = validate_storymap_json(storymap_json)
    if errors:
        print("Warning: JSON validation errors:")
        for error in errors:
            print(f"  - {error}")

    return storymap_json


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

