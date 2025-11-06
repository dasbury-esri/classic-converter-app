"""
StoryMap JSON Schema and Templates

This module contains the JSON structure templates and constants for creating
ArcGIS StoryMaps directly from JSON without using the Python API.
"""

import uuid
from typing import Any, Dict, List, Optional


def generate_node_id() -> str:
    """Generate a unique node ID in the format used by StoryMaps"""
    return f"n-{uuid.uuid4().hex[:6]}"


def generate_resource_id() -> str:
    """Generate a unique resource ID"""
    return f"r-{uuid.uuid4().hex[:6]}"


# Base StoryMap structure
def create_base_storymap_json() -> Dict[str, Any]:
    """
    Create the base JSON structure for a new StoryMap

    This mimics the structure created by StoryMap()._properties
    """
    root_node_id = generate_node_id()
    cover_node_id = generate_node_id()
    nav_node_id = generate_node_id()
    credits_node_id = generate_node_id()
    theme_resource_id = generate_resource_id()

    return {
        "root": root_node_id,
        "nodes": {
            root_node_id: {
                "type": "story",
                "data": {
                    "storyTheme": theme_resource_id  # Link to theme resource
                },
                "children": [cover_node_id, nav_node_id, credits_node_id]
            },
            cover_node_id: {
                "type": "storycover",  # NOT "cover"
                "data": {
                    "type": "minimal"
                }
            },
            nav_node_id: {
                "type": "navigation",
                "data": {
                    "links": []  # Auto-populated by StoryMaps
                },
                "config": {
                    "isHidden": True  # Python True, not JavaScript true
                }
            },
            credits_node_id: {
                "type": "credits",
                "children": []
            }
        },
        "resources": {
            theme_resource_id: {
                "type": "story-theme",
                "data": {
                    "themeId": "summit"
                }
            }
        },
        "config": {
            "size": "large"
        }
    }


# Node templates
def create_text_node(text: str, style: str = "paragraph", alignment: str = "start") -> Dict[str, Any]:
    """
    Create a text node

    Args:
        text: HTML text content
        style: Text style (h1, h2, h3, h4, paragraph, quote)
        alignment: Text alignment (start, center, end)
    """
    return {
        "type": "text",
        "data": {
            "type": style,
            "text": text,
            "textAlignment": alignment
        }
    }


def create_image_node(resource_id: str, caption: Optional[str] = None,
                     alt: Optional[str] = None, display: str = "standard",
                     float_alignment: str = "start") -> Dict[str, Any]:
    """
    Create an image node

    Args:
        resource_id: Resource ID for the image
        caption: Optional caption
        alt: Optional alt text (schema uses 'alt', not 'altText')
        display: Display mode (standard, wide, full, float)
        float_alignment: Alignment when display is 'float' (start, end)
    """
    node = {
        "type": "image",
        "config": {
            "size": display
        },
        "data": {
            "image": resource_id
        }
    }

    if display == "float":
        node["config"]["floatAlignment"] = float_alignment

    if caption:
        node["data"]["caption"] = caption

    if alt:
        node["data"]["alt"] = alt  # Schema uses 'alt', not 'altText'

    return node


def create_map_node(resource_id: str, extent: Optional[Dict] = None,
                   viewpoint: Optional[Dict] = None, zoom: Optional[int] = None,
                   map_layers: Optional[List[Dict]] = None,
                   show_legend: bool = False, show_search: bool = False) -> Dict[str, Any]:
    """
    Create a map node

    Args:
        resource_id: Resource ID for the map
        extent: Map extent dictionary
        viewpoint: Viewpoint dictionary
        zoom: Zoom level
        map_layers: Layer visibility settings (list of dicts with id, title, visible)
        show_legend: Whether to show legend widget
        show_search: Whether to show search widget
    """
    node = {
        "type": "webmap",  # Schema shows type is "webmap"
        "config": {
            "size": "standard"
        },
        "data": {
            "map": resource_id
        }
    }

    # Widget toggles
    if show_legend:
        node["data"]["isShowingLegend"] = True
    if show_search:
        node["data"]["search"] = True

    # Map layers with proper structure
    if map_layers:
        node["data"]["mapLayers"] = [
            {
                "id": layer["id"],
                "title": layer.get("title", ""),
                "visible": layer.get("visible", True)
            }
            for layer in map_layers
        ]

    if extent:
        node["data"]["extent"] = extent

    if viewpoint:
        node["data"]["viewpoint"] = viewpoint

    if zoom is not None:
        node["data"]["zoom"] = zoom

    return node


def create_embed_node(url: str, embed_type: str = "video",
                     display: str = "card", caption: Optional[str] = None,
                     alt: Optional[str] = None, title: Optional[str] = None,
                     description: Optional[str] = None, thumbnail_url: Optional[str] = None,
                     provider_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Create an embed node

    Args:
        url: URL for the embed (goes directly in node, NOT as resource)
        embed_type: Embedly type (link, video, rich, photo, pdf)
        display: Display mode (card, inline)
        caption: Optional caption
        alt: Optional alt text (schema uses 'alt', not 'altText')
        title: Optional embed title
        description: Optional embed description
        thumbnail_url: Optional thumbnail URL
        provider_url: Optional provider URL
    """
    # Parse domain from URL for provider_url if not provided
    if not provider_url and url:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            provider_url = f"{parsed.scheme}://{parsed.netloc}"
        except:
            provider_url = ""

    node = {
        "type": "embed",
        "config": {
            "size": "standard"
        },
        "data": {
            "url": url,  # URL goes directly in node data
            "display": display,
            "embedType": embed_type,
            "isEmbedSupported": True,
            "embedSrc": url,  # Same as url
            "allowSmallEmbeds": True
        }
    }

    if caption:
        node["data"]["caption"] = caption

    if alt:
        node["data"]["alt"] = alt  # Schema uses 'alt', not 'altText'

    if title:
        node["data"]["title"] = title

    if description:
        node["data"]["description"] = description

    if thumbnail_url:
        node["data"]["thumbnailUrl"] = thumbnail_url

    if provider_url:
        node["data"]["providerUrl"] = provider_url

    return node

def create_tour_map_geometry(id: str, long: float, lat: float,
                            type: str = "POINT_NUMBERED_TOUR",
                            scale: float = None,
                            viewpoint: dict = None) -> Dict[str, Any]:
    """
    Create a single geometry point for a tour-map node.

    Args:
        id: Unique geometry ID
        long: Longitude value
        lat: Latitude value
        type: Geometry type (default "POINT_NUMBERED_TOUR")
        scale: Optional scale value
        viewpoint: Optional viewpoint dict

    Returns:
        Dict representing a geometry point
    """
    geometry = {
        "id": id,
        "type": type,
        "nodes": [
            {
                "long": long,
                "lat": lat
            }
        ]
    }
    if scale is not None:
        geometry["scale"] = scale
    if viewpoint is not None:
        geometry["viewpoint"] = viewpoint
    return geometry

def create_tour_map_node(geometries: Dict[str, Any], mode: str = "2d", 
                         basemap_type: str = "name", basemap_value: str = "worldImagery", 
                         alt: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a tour-map node matching the structure in tour-nativeAGSM.json

    Args:
        geometries: Dict of geometry objects (id: geometry dict)
        mode: Map mode (default "2d")
        basemap_type: Basemap type (default "name")
        basemap_value: Basemap value (default "worldImagery")
        alt: Optional alt text

    Returns:
        Dict representing a tour-map node
    """
    node = {
        "type": "tour-map",
        "data": {
            "geometries": geometries,
            "mode": mode,
            "basemap": {
                "type": basemap_type,
                "value": basemap_value
            }
        }
    }
    if alt:
        node["data"]["alt"] = alt
    return node

def create_tour_node(
    places: List[str], map_node_id: str,
    accent_color: str,
    narrative_panel_position: str = "start", narrative_panel_size: str = "medium",
    tour_type: str = "explorer", subtype: str = "list") -> Dict[str, Any]:
    """
    Create a tour node matching the structure in tour-nativeAGSM.json.

    Args:
        places: List of place dicts, each with keys: id, featureId, contents, media, title
        map_node_id: Node ID of the associated tour-map node
        narrative_panel_position: Position of the narrative panel ("start" by default)
        narrative_panel_size: Size of the narrative panel ("medium" by default)
        accent_color: Accent color hex string
        tour_type: Type of tour ("explorer" by default)
        subtype: Subtype of tour ("list" by default)

    Returns:
        Dict representing a tour node
    """
    node = {
        "type": "tour",
        "data": {
            "type": tour_type,
            "subtype": subtype,
            "narrativePanelPosition": narrative_panel_position,
            "map": map_node_id,
            "places": places,
            "narrativePanelSize": narrative_panel_size,
            "accentColor": accent_color
        }
    }

    return node

def create_tour_place(
    id: str,
    feature_id: str,
    contents: list,
    media: str,
    title: str
) -> dict:
    """
    Create a single place dict for a tour node.

    Args:
        id: Node ID for the place
        feature_id: Geometry feature ID
        contents: List of node IDs for content
        media: Node ID for media
        title: Node ID for title

    Returns:
        Dict representing a place
    """
    if media is None or title is None:
        raise ValueError("Media and title are required for a tour place when converting")
    place = {
        "id": id,
        "featureId": feature_id,
        "contents": contents,
        "media": media,
        "title": title
    }
    return place

def create_gallery_node(image_node_ids: List[str], caption: Optional[str] = None,
                       alt: Optional[str] = None,
                       layout: str = "square-dynamic") -> Dict[str, Any]:
    """
    Create a gallery node

    Args:
        image_node_ids: List of image NODE IDs (not resource IDs!)
        caption: Optional caption
        alt: Optional alt text (schema uses 'alt', not 'altText')
        layout: Gallery layout (square-dynamic, jigsaw, filmstrip)

    Note: Gallery children are node IDs of image nodes, not resource IDs.
          Schema requires 1-12 images and galleryLayout is REQUIRED.
    """
    if len(image_node_ids) < 1 or len(image_node_ids) > 12:
        raise ValueError("Gallery must have 1-12 images")

    node = {
        "type": "gallery",
        "config": {
            "size": "standard"
        },
        "data": {
            "galleryLayout": layout  # REQUIRED by schema!
        },
        "children": image_node_ids  # Node IDs, NOT resource IDs!
    }

    if caption:
        node["data"]["caption"] = caption

    if alt:
        node["data"]["alt"] = alt  # Schema uses 'alt', not 'altText'

    return node


def create_separator_node() -> Dict[str, Any]:
    """Create a separator node"""
    return {
        "type": "separator",
        "data": {}
    }

def create_carousel_node(children: List[Dict[str, Any]]) -> Dict[str, Any]:
    """A component that handles rendering media items in a carousel layout."""
    node = {
        "type": 'carousel',
        "config": {},
        "data": {},
        "children": children[:5]  # array of up to 5 images
    }
    return node

def create_sidecar_structure(sidecar_type: str = "docked-panel") -> tuple:
    """
    Create a complete sidecar structure with IDs

    Args:
        sidecar_type: Type of sidecar (docked-panel, floating-panel)

    Returns:
        Tuple of (sidecar_id, slide_id, narrative_id, nodes_dict)
    """
    sidecar_id = generate_node_id()
    slide_id = generate_node_id()
    narrative_id = generate_node_id()

    nodes = {
        sidecar_id: {
            "type": "immersive",
            "data": {
                "type": "sidecar",
                "subtype": sidecar_type
            },
            "children": [slide_id]
        },
        slide_id: {
            "type": "immersive-slide",
            "data": {
                "transition": "fade"
            },
            "children": [narrative_id]
        },
        narrative_id: {
            "type": "immersive-narrative-panel",
            "data": {
                "position": "start",  # Required by real structure
                "size": "small",      # Required by real structure
                "panelStyle": "themed"
            },
            "children": []
        }
    }

    return sidecar_id, slide_id, narrative_id, nodes


def create_slide_structure() -> tuple:
    """
    Create a single slide structure for adding to a sidecar

    Returns:
        Tuple of (slide_id, narrative_id, nodes_dict)
    """
    slide_id = generate_node_id()
    narrative_id = generate_node_id()

    nodes = {
        slide_id: {
            "type": "immersive-slide",
            "data": {
                "transition": "fade"
                # NO media property - media node goes in children!
            },
            "children": [narrative_id]  # Media will be appended after narrative
        },
        narrative_id: {
            "type": "immersive-narrative-panel",
            "data": {
                "position": "start",  # Required by real structure
                "size": "small",      # Required by real structure
                "panelStyle": "themed"
            },
            "children": []
        }
    }

    return slide_id, narrative_id, nodes


# Resource templates
def create_image_resource(file_path: str, width: int = 1024, height: int = 1024) -> Dict[str, Any]:
    """
    Create an image resource

    Args:
        file_path: Local file path or URL
        width: Image width (default: 1024)
        height: Image height (default: 1024)
    """
    # Extract filename from path
    import os
    filename = os.path.basename(file_path)

    return {
        "type": "image",
        "data": {
            "resourceId": filename,  # Just filename, NOT full path
            "provider": "item-resource",
            "height": height,
            "width": width
        }
    }


def create_map_resource(item_id: str, item_type: str = "webmap") -> Dict[str, Any]:
    """
    Create a map resource

    Args:
        item_id: ArcGIS item ID for the map
        item_type: Type of map (webmap, webscene)
    """
    return {
        "type": "webmap" if item_type == "webmap" else "webscene",
        "data": {
            "type": "minimal",
            "itemId": item_id,
            "itemType": item_type
        }
    }


# NOTE: Embed resources removed - embeds use URL directly in node data per schema


def create_theme_resource(theme_id: str, is_custom: bool = False) -> Dict[str, Any]:
    """
    Create a theme resource

    Args:
        theme_id: Theme identifier
        is_custom: Whether this is a custom theme (item ID) or standard theme
    """
    resource = {
        "type": "story-theme",
        "data": {}
    }

    if is_custom:
        resource["data"]["themeItemId"] = theme_id
    else:
        resource["data"]["themeId"] = theme_id

    return resource


# Cover configuration
def create_cover_config(title: str, summary: str = "", by_line: str = "",
                       image_resource_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Create cover node configuration

    Args:
        title: Cover title
        summary: Cover summary/subtitle
        by_line: Author byline
        image_resource_id: Optional background image resource ID
    """
    config = {
        "type": "minimal",
        "title": title,
        "summary": summary,
        "byline": by_line
    }

    if image_resource_id:
        config["image"] = image_resource_id

    return config


# Constants for mappings
TEXT_STYLES = {
    "h1": "h1",  # Use tag name directly, not "heading"
    "h2": "h2",  # Use tag name directly, not "subheading"
    "h3": "h3",
    "h4": "h4",
    "p": "paragraph",
    "blockquote": "quote"
}

ALIGNMENTS = {
    "left": "start",
    "center": "center",
    "right": "end"
}

EMBEDLY_TYPES = {
    "video": "video",
    "webpage": "link"
}

STANDARD_THEMES = [
    "summit", "obsidian", "mesa",
    "ridgeline", "tidal", "slate"
]

SIDECAR_TYPES = {
    "journal": "docked-panel",
    "series": "docked-panel",
    "cascade_immersive": "floating-panel"
}


# Helper functions for JSON manipulation
def insert_node_before_credits(storymap_json: Dict[str, Any], node_id: str) -> None:
    """
    Insert a node into the story before the credits node

    Args:
        storymap_json: The storymap JSON structure
        node_id: The node ID to insert
    """
    root_id = storymap_json["root"]
    children = storymap_json["nodes"][root_id]["children"]

    # Insert before last element (credits)
    # Structure is: [cover, navigation, ...content..., credits]
    children.insert(-1, node_id)


def add_child_to_node(storymap_json: Dict[str, Any], parent_id: str, child_id: str) -> None:
    """
    Add a child to a node's children array

    Args:
        storymap_json: The storymap JSON structure
        parent_id: Parent node ID
        child_id: Child node ID to add
    """
    parent_node = storymap_json["nodes"][parent_id]

    if "children" not in parent_node:
        parent_node["children"] = []

    parent_node["children"].append(child_id)


def set_cover_data(storymap_json: Dict[str, Any], title: str, summary: str = "",
                  by_line: str = "", image_resource_id: Optional[str] = None) -> None:
    """
    Set the cover data in the storymap JSON

    Args:
        storymap_json: The storymap JSON structure
        title: Cover title
        summary: Cover summary
        by_line: Author byline
        image_resource_id: Optional image resource ID
    """
    # Find cover node
    root_id = storymap_json["root"]
    cover_id = None

    for node_id in storymap_json["nodes"][root_id]["children"]:
        if storymap_json["nodes"][node_id]["type"] in ["cover", "storycover"]:
            cover_id = node_id
            break

    if cover_id:
        cover_config = create_cover_config(title, summary, by_line, image_resource_id)
        storymap_json["nodes"][cover_id]["data"] = cover_config


def set_theme(storymap_json: Dict[str, Any], theme_id: str) -> None:
    """
    Set or update the theme in the storymap JSON

    Args:
        storymap_json: The storymap JSON structure
        theme_id: Theme ID (standard or custom)
    """
    is_custom = theme_id not in STANDARD_THEMES

    # Find or create theme resource
    theme_resource_id = None

    for resource_id, resource in storymap_json["resources"].items():
        if resource["type"] == "story-theme":
            theme_resource_id = resource_id
            break

    if not theme_resource_id:
        theme_resource_id = generate_resource_id()
        storymap_json["resources"][theme_resource_id] = create_theme_resource(theme_id, is_custom)
    else:
        storymap_json["resources"][theme_resource_id] = create_theme_resource(theme_id, is_custom)


def validate_node_against_schema(node: Dict[str, Any], node_type: str) -> List[str]:
    """
    Validate node structure against schema requirements

    Args:
        node: Node dictionary to validate
        node_type: Type of node (image, embed, gallery, webmap, etc.)

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    if node_type == "image":
        if "image" not in node.get("data", {}):
            errors.append("Image node missing data.image resource ID")
        if "altText" in node.get("data", {}):
            errors.append("Image node uses altText instead of alt (schema violation)")

    if node_type == "embed":
        if "url" not in node.get("data", {}):
            errors.append("Embed node missing required data.url")
        if "altText" in node.get("data", {}):
            errors.append("Embed node uses altText instead of alt (schema violation)")
        if "isEmbedSupported" not in node.get("data", {}):
            errors.append("Embed node missing isEmbedSupported flag")

    if node_type == "gallery":
        if "galleryLayout" not in node.get("data", {}):
            errors.append("Gallery node missing REQUIRED data.galleryLayout")
        if "children" not in node:
            errors.append("Gallery node missing children array")
        elif len(node["children"]) < 1 or len(node["children"]) > 12:
            errors.append(f"Gallery must have 1-12 children, has {len(node['children'])}")

    if node_type == "webmap":
        if "map" not in node.get("data", {}):
            errors.append("Map node missing data.map resource ID")

    if node_type == "tour-map":
        data = node.get("data", {})
        if "geometries" not in data:
            errors.append("Tour-map node missing data.geometries")
        else:
            for geom_id, geom in data["geometries"].items():
                if "id" not in geom:
                    errors.append(f"Geometry '{geom_id}' missing 'id'")
                if "type" not in geom:
                    errors.append(f"Geometry '{geom_id}' missing 'type'")
                if "nodes" not in geom or not isinstance(geom["nodes"], list) or len(geom["nodes"]) == 0:
                    errors.append(f"Geometry '{geom_id}' missing or invalid 'nodes' list")
                for node_pt in geom["nodes"]:
                    if "lat" not in node_pt or "long" not in node_pt:
                        errors.append(f"Geometry '{geom_id}' node missing 'lat' or 'long'")

    if node_type == "tour":
        data = node.get("data", {})
        if "places" not in data or not isinstance(data["places"], list) or len(data["places"]) == 0:
            errors.append("Tour node missing or empty data.places list")
        for place in data.get("places", []):
            if "id" not in place:
                errors.append("Place missing 'id'")
            if "featureId" not in place:
                errors.append(f"Place '{place.get('id', '?')}' missing 'featureId'")
            if "contents" not in place or not isinstance(place["contents"], list) or len(place["contents"]) == 0:
                errors.append(f"Place '{place.get('id', '?')}' missing or empty 'contents' list")
            if "media" not in place:
                errors.append(f"Place '{place.get('id', '?')}' missing 'media'")
            if "title" not in place:
                errors.append(f"Place '{place.get('id', '?')}' missing 'title'")


    return errors


def validate_storymap_json(storymap_json: Dict[str, Any]) -> List[str]:
    """
    Validate the storymap JSON structure

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Check required keys
    if "root" not in storymap_json:
        errors.append("Missing 'root' key")

    if "nodes" not in storymap_json:
        errors.append("Missing 'nodes' key")

    if "resources" not in storymap_json:
        errors.append("Missing 'resources' key")

    if errors:
        return errors

    # Check root node exists
    root_id = storymap_json.get("root")
    if root_id not in storymap_json["nodes"]:
        errors.append(f"Root node '{root_id}' not found in nodes")

    # Check all node references
    for node_id, node in storymap_json["nodes"].items():
        if "children" in node:
            for child_id in node["children"]:
                if child_id not in storymap_json["nodes"]:
                    errors.append(f"Child node '{child_id}' not found (referenced by '{node_id}')")

    # Check resource references
    for node_id, node in storymap_json["nodes"].items():
        node_data = node.get("data", {})
        node_type = node.get("type")

        # Validate node against schema
        node_errors = validate_node_against_schema(node, node_type)
        errors.extend(node_errors)

        # Check image resources
        if node_type == "image" and "image" in node_data:
            resource_id = node_data["image"]
            if resource_id not in storymap_json["resources"]:
                errors.append(f"Image resource '{resource_id}' not found (referenced by node '{node_id}')")

        # Check map resources
        if node_type in ["webmap", "map"] and "map" in node_data:
            resource_id = node_data["map"]
            if resource_id not in storymap_json["resources"]:
                errors.append(f"Map resource '{resource_id}' not found (referenced by node '{node_id}')")

        # Check story theme reference
        if node_type == "story" and "storyTheme" in node_data:
            theme_resource_id = node_data["storyTheme"]
            if theme_resource_id not in storymap_json["resources"]:
                errors.append(f"Theme resource '{theme_resource_id}' not found (referenced by story node)")

    return errors

