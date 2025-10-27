classic_story_id = "" # Enter the ItemId in the quotes to the left
#Standard Themes = summit,obsidian,mesa,ridgeline,tidal,slate
theme_id = "summit"
portal = "https://www.arcgis.com" #default
username = ""
password = ""
import glob
import html
import json
import os
import re
import urllib
import uuid

from arcgis.apps.storymap import Scales, StoryMap, TextStyles
from arcgis.apps.storymap import story_content as sc
#Imports
from arcgis.gis import GIS, Item
from arcgis.mapping import WebMap, WebScene
from arcgis.widgets import MapView
from bs4 import BeautifulSoup, NavigableString, Tag

textStyleMapping = {
    "h1": TextStyles.HEADING,
    "h2": TextStyles.SUBHEADING,
    "p": TextStyles.PARAGRAPH,
    "blockquote": TextStyles.QUOTE,
}
alignmentMapping = {
    "left": "start",
    "center": "center",
    "right": "end",
}
from arcgis.gis import GIS

if username == "":
    gis_conn = GIS("home")
else:
    gis_conn = GIS(portal, username, password)

def force_valid_python_string(input_string):
    # Escape special characters
    escaped_string = input_string.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')

    # Enclose the string in quotes
    valid_string = f'"{escaped_string}"'

    return valid_string

def replace_single_quotes(json_obj):
    if isinstance(json_obj, dict):
        new_obj = {}
        for key, value in json_obj.items():
            if isinstance(key, str):
                key = key.replace("'", '"')
            new_obj[key] = replace_single_quotes(value)
        return new_obj
    elif isinstance(json_obj, list):
        return [replace_single_quotes(item) for item in json_obj]
    elif isinstance(json_obj, str):
        return json_obj.replace("'", '"')
    else:
        return json_obj

def is_nonempty_string(string):
    # Check if the string is not empty
    if len(string.strip()) > 0:
        return True
    return False

def remove_span_tags(data):
    """Remove non-essential HTML tags from content

    Wraps content in a temporary div to ensure safe DOM manipulation
    and prevent issues with document-level nodes.
    """
    accepted_tags = ['strong','em','ol','li','ul','a','img']
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
        return ''.join(str(child) for child in wrapper.children).replace("\n","")
    elif isinstance(data, dict):
        cleaned_data = {}
        for key, value in data.items():
            cleaned_data[key] = remove_span_tags(value)
        return cleaned_data
    elif isinstance(data, list):
        return [remove_span_tags(item) for item in data]
    else:
        return data

def add_empty_sidecar(agsm_storymap, type="docker-panel"):
    """
    This will take your new story and add an empty sidecar to your story. The ability to add new_sidecars using a built in method will be available in the next python API version
    """
    side_car_node = f"n-{uuid.uuid4().hex[:6]}"
    narrative_node = f"n-{uuid.uuid4().hex[:6]}"
    slide_node = f"n-{uuid.uuid4().hex[:6]}"
    story_nodeid = agsm_storymap._properties['root']
    agsm_storymap._properties['nodes'][story_nodeid]['children'].insert(-2,side_car_node)
    agsm_storymap.properties['nodes'][narrative_node] = {
            "type": "immersive-narrative-panel",
            "data": {
                "panelStyle": "themed"
            }
        }
    agsm_storymap._properties['nodes'][slide_node] = {
            "type": "immersive-slide",
            "data": {
                "transition": "fade"
            },
            "children": [
                narrative_node
            ]
        }
    agsm_storymap._properties['nodes'][side_car_node] = {
            "type": "immersive",
            "data": {
                "type": "sidecar",
                "subtype": type,
                #"narrativePanelPosition": "start",
                #"narrativePanelSize": "small"
            },
            "children": [
                slide_node
            ]
        }
    return side_car_node, slide_node, narrative_node

def determine_scale_level(given_extent,scale_cofficient=4.4):
    """
    This function is used for the 2.1.0.2 version of the python API,
    Could be deprecated in the next release when set_viewpoint is updated
    scale_cofficient is approximate for web mercator web maps
    """
    ymax = given_extent['ymax']
    ymin = given_extent['ymin']
    map_scale = ymax-ymin
    map_scale = map_scale*scale_cofficient
    map_int_scale = map_scale
    max_scale = 147914382
    for scale in Scales:
        if int(map_scale) < int(scale.value['scale']):
            max_scale = scale.value['scale']
            map_int_scale = max_scale
        else:
            map_scale = scale
            #print(f"found {map_scale} scale")
            return map_scale, map_int_scale
def determine_scale_zoom_level(given_extent,scale_cofficient=4.4):
    max_scale = 147914382
    if given_extent is None:
        return None, None
    if 'ymax' not in given_extent or 'ymin' not in given_extent:
        return None, None
    ymax = given_extent['ymax']
    ymin = given_extent['ymin']
    map_scale = ymax-ymin
    map_scale = map_scale*scale_cofficient
    map_int_scale = map_scale

    for scale in Scales:
        if int(map_scale) < int(scale.value['scale']):
            max_scale = scale.value['scale']
            map_int_scale = max_scale
            map_zoom = scale.value['zoom']
        else:
            map_scale = max_scale
            map_zoom  = map_zoom
            #print(f"found {map_scale} scale")
            return map_scale, map_zoom

def process_img_tag(src):
    """Process an image url. If url is a AGO resource, Download locally and upload with new story map in order to conserve images.
    If not an AGO resource return the src url.

    Args:
        src (string): URL of image

    Returns:
        string: URL or local path for image
    """
    src_url = src.replace(" ","%20")
    image_url = src_url
    if image_url.startswith('https://www.arcgis.com/sharing/rest/content'):
        postfix = image_url.split('.')[-1]
        image_url = image_url+f'?token={gis_conn._portal.con.token}'
        media_path = f'{uuid.uuid4()}.{postfix}' # Generate new file name consistant with current ArcGIS StoryMaps resource model
        urllib.request.urlretrieve(image_url,media_path)
    elif image_url.startswith("//www.arcgis.com/sharing/rest/content"):
        postfix = image_url.split('.')[-1]
        image_url = "https:"+ image_url+f'?token={gis_conn._portal.con.token}'
        media_path = f'{uuid.uuid4()}.{postfix}' # Generate new file name consistant with current ArcGIS StoryMaps resource model
        urllib.request.urlretrieve(image_url,media_path)
    else:
        if src_url.startswith('https://'):
            return src_url
        else:
            return f'https:{src_url}'
    return media_path

def convert_series_or_journal(classic_story_id,theme_id="summit"):
    """
    Main function for notebook, This takes a story ID for a classic Journal or Series StoryMap and creates a ArcGIS StoryMap with the content of the classic story in the logged in User's account

    Args:
        classic_story_id (string): string id of classic story

    Returns:
        string: URL or local path for image
    """


    #---------------------------------------------------------
    # Set Method Attributes
    #---------------------------------------------------------
    type_dict = {
    'image': sc.Image,
    'video': sc.Video,
    'embed': sc.Embed,
    'webmap': sc.Map
    }

    """
    Due to the need to add nodes to a story first and then update properties,
    properties/settings are tracked in the following dictionaries to be used to update the story at the end of the run
    """
    map_setting_dict = {} #Tracking dictionary for map settings
    embed_settings_dict = {}#Tracking dictionary for embeds
    image_settings_dict = {}#Tracking dictionary for images
    """Track locally created stories for deletion"""
    local_images = [] #Tracking dictionary for uploaded images

    #---------------------------------------------------------
    # Get StoryMap that has an empty Sidecar to copy
    #---------------------------------------------------------
    """For the current version of python a empty sidecar needs to be copied from a story.
    This can be removed and replaced with a created sidecar be updated post v2.1.0.2"""
    new_storymap = StoryMap()
    sidecar_id, slide_, narrative_ = add_empty_sidecar(new_storymap, type='docked-panel')
    story_sidecar = new_storymap.get(sidecar_id)
    #---------------------------------------------------------
    #Get Classic StoryMap and data for conversion
    #---------------------------------------------------------
    classic_journal_item = Item(gis=gis_conn,itemid=classic_story_id)
    classic_keywords = classic_journal_item.typeKeywords

    # Determine the Classic type to allow for slight data model differences to be addressed later. Raise exception if not Journal or Series
    if 'MapJournal' in classic_keywords or 'mapjournal' in classic_keywords:
        classic_type = 'journal'
    elif 'MapSeries'in classic_keywords or 'mapseries' in classic_keywords:
        classic_type = 'series'
    else:
        raise Exception('Sorry this code only support MapJournal and MapSeries Classic StoryMaps')
    classic_journal_data = classic_journal_item.get_data()
    journal_title = classic_journal_data.get('values').get('title')
    print(f"Converting {journal_title}")

    print(classic_type)
    #get sections based on type
    if classic_type == 'journal':
        list_of_sections = classic_journal_data.get('values').get('story').get('sections')
    elif classic_type == 'series':
        list_of_sections = classic_journal_data.get('values').get('story').get('entries')

    #---------------------------------------------------------
    # Loop Through classic sections and add content
    #---------------------------------------------------------
    for section in list_of_sections:
        actually_embed = False
        #determine slide media:
        #---------------------------------------------------------
        # Determine Slide Media Content - Map,Image,Video,Embed
        #---------------------------------------------------------
        media_type = section.get('media').get('type')
        # Video and Webpage in classic stories are converted to EMBEDS for ArcGIS StoryMaps
        if media_type in ['video','webpage']:
            actually_embed=True

        #---------------------------------------------------------
        # Handle Slide Media Content - Map
        #---------------------------------------------------------
        if media_type == 'webmap':
            has_search = True #REMOVE
            #Set default scales for use in v2.1.0.2 set_viewpoint and map properties
            map_scale = Scales.CONTINENT
            map_int_scale = 147914382
            #Get settings from webmap section
            has_legend = section.get('media').get('webmap').get('legend', False).get('enable',False)
            map_extent = section.get('media').get('webmap').get('extent',{})
            map_layers = section.get('media').get('webmap').get('layers',{})
            #Get Map itemID in AGO/Portal
            map_id = section.get('media').get('webmap').get('id')
            #Generate Map Content as a AGSM node
            map_node = sc.Map(item=map_id)
            map_item = Item(gis=gis_conn,itemid=map_id)
            #if no map extent information is found in the classic map, find extent of the AGO/Portal item and add to settings dict
            #This includes scale calculations
            if map_extent is None:
                if map_item.type == "Web Map":
                    map_webapp = WebMap(map_item)
                    if map_webapp._webmapdict.get('initialState',None) is not None:
                        map_extent = map_webapp._webmapdict["initialState"]["viewpoint"]['targetGeometry']
                        map_scale, max_int_scale = determine_scale_level(given_extent=map_extent)
            else:
                #If extent available, calculate scale from map extent
                map_scale, max_int_scale = determine_scale_level(given_extent=map_extent)
            #Add calculated map settings to dictionary
            map_setting_dict[map_node.node] = {'show_legend' : has_legend,'show_search':has_search, 'map_extent': map_extent, 'scale':map_scale, 'layers':map_layers, 'int_scale':map_int_scale}
            #Set Map Node as Sidecar Slide media
            slide_media = map_node

        else:
            media_path = section.get('media').get(media_type).get('url')
            iframe = section.get('media').get(media_type).get('frameTag')
            if iframe != None:
                iframe_soup = BeautifulSoup(iframe,'html.parser')
                iframe_src = iframe_soup.find('iframe')['src']
                if iframe_src != None:
                    media_path = iframe_src
            url = media_path.strip("/")
            altext = section.get('media').get(media_type).get('altText')
            created_local = False
            if media_type == 'image' and 'www.arcgis.com/sharing/rest/content' in media_path:
                created_local = True
                media_path = process_img_tag(media_path)
            #set estimated embedlyTypes and set type to embed if actually_embed = True
            embedly_type = 'link'
            if actually_embed:
                if media_type == 'webpage':
                    embedly_type = 'link'
                elif media_type == 'video':
                    embedly_type = 'video'
                media_type='embed'
            if created_local:
                #Add locally created resource to local_images list for later deletion
                local_images.append(media_path)
            #ArcGIS StoryMaps requires https:// URL's
            if not media_path.startswith("https://") and not created_local:
                media_path = "https://" + media_path
            #Set slide media
            if media_path == "https://":
                slide_media = type_dict[media_type](path=f'https://www.example.com/')
            else:
                slide_media = type_dict[media_type](path=f'{media_path}')
            #Add embedlyType to embed settings
            if media_type == 'embed':
                embed_node = slide_media
                embed_settings_dict[embed_node.node] = {'embedly_type': embedly_type}

        #Section content will be tracked add added to the sidecar slide using the list below
        section_content_for_slide = []
        #add Title
        section_title = BeautifulSoup(section.get('title'),'html.parser')
        section_title_for_panel = sc.Text(section_title.text,style=TextStyles.HEADING)
        section_content_for_slide.append(section_title_for_panel)

        #---------------------------------------------------------
        # Determine Narratice Media Content - Image,Video,Embed,Text
        #---------------------------------------------------------
        if classic_type == 'journal':
            section_content = section.get('content')
        elif classic_type == 'series':
            section_content = section.get('description')

        content_html = BeautifulSoup(section_content,'html.parser')
        for el in content_html.children:
            try:
                if el.name == None:
                    pass #pass instances where BS4 creates None tags
                elif el.has_attr('class'):
                    #handle caption encapsulated elements
                    if el.name == 'p':
                        if el != None and len(str(el)) > 8:
                            p_string = (str(el))
                            p_cleaner = (r'<p.*>|<\/p?>')
                            #cleaned_string = re.sub(p_cleaner,'', p_string)
                            cleaned_string = remove_span_tags(p_string)
                            cleaned_string.replace('"',"")
                            if is_nonempty_string(cleaned_string):
                                section_content_for_slide.append(sc.Text(text=cleaned_string,style=TextStyles.PARAGRAPH))
                    if el['class'][0] == 'caption' or 'image-container' in el['class']:
                        for child in el.findChildren(recusive=False):
                            #Handle image tag
                            if child.name == 'img':
                                has_image = True
                                image_url = child['src']
                                media_path = image_url
                                if "www.arcgis.com/sharing/rest/content"in image_url:
                                    media_path= process_img_tag(image_url)
                                for caption_child in el.findChildren('figcaption'):#CAN BE REMOVED
                                    caption_string = caption_child.string
                                if has_image:
                                    #content_image.caption = caption_string
                                    section_content_for_slide.append(sc.Image(path=media_path))
                                if not media_path.startswith('https'):
                                    local_images.append(media_path)
                            elif child.name == 'p':
                                if child != None and len(child.text) > 8:
                                    p_string = (str(child))
                                    p_cleaner = (r'<p.*>|<\/p?>')
                                    cleaned_string = re.sub(p_cleaner,'', p_string)
                                    cleaned_string = remove_span_tags(p_string)
                                    cleaned_string.replace('"',"")
                                    if is_nonempty_string(cleaned_string):
                                        section_content_for_slide.append(sc.Text(text=cleaned_string,style=TextStyles.PARAGRAPH))
                            #handle divs containing strings
                            elif child.name == 'div':
                                p_string = (str(child))
                                p_string = remove_span_tags(p_string)
                                p_cleaner = (r'<p.*>|<\/p?>')
                                cleaned_string = re.sub(p_cleaner,'', p_string)
                                cleaned_string = remove_span_tags(cleaned_string)
                                cleaned_string = cleaned_string.replace('"',"")
                                if is_nonempty_string(cleaned_string):
                                    section_content_for_slide.append(sc.Text(text=cleaned_string,style=TextStyles.PARAGRAPH))
                        if el.find('span'):
                            span_element = el.find('span')
                            span_element.unwrap()
                            span_string = (str(span_element)).replace('"',"")
                            span_string = force_valid_python_string(span_string)
                            section_content_for_slide.append(sc.Text(text=span_string,style=TextStyles.PARAGRAPH))
                    #Handle Video And Embeds
                    elif 'iframe-container' in el['class']:
                        display_type = 'card'
                        embed_type = 'link'
                        if 'mj-video-by-url' in el['class']:
                            display_type = 'inline'
                            embedly_type = 'video'

                        is_embed = True
                        iframe_el = el.find('iframe')
                        embed_url = iframe_el['src'].strip("/")
                        section_content_for_slide.append(sc.Embed(path=embed_url))
                        embed_node = section_content_for_slide[-1]
                        embed_settings_dict[embed_node.node] = {'embedly_type': f'{embedly_type}', 'display':f'{display_type}'}
                #Handle Images without Captions
                elif el.name == 'img':
                    image_url = el['src']
                    media_path = process_img_tag(src=image_url)
                    section_content_for_slide.append(sc.Image(path=media_path))
                    if not media_path.startswith('https'):
                        local_images.append(media_path)
                #handle paragraph tags
                elif el.name == 'p':
                    for img in el.findChildren('img'):
                        image_url = img['src']
                        media_path = process_img_tag(src=image_url)
                        section_content_for_slide.append(sc.Image(path=media_path))
                        if not media_path.startswith('https'):
                            local_images.append(media_path)

                    if el != None and len(el.text) > 8:
                        p_string = (str(el))
                        p_cleaner = (r'<p.*>|<\/p?>')
                        cleaned_string = re.sub(p_cleaner,'', p_string)
                        cleaned_string = remove_span_tags(p_string)
                        cleaned_string = cleaned_string.replace('"',"")
                        if is_nonempty_string(cleaned_string):
                            section_content_for_slide.append(sc.Text(text=cleaned_string,style=TextStyles.PARAGRAPH))

                #handle divs containing strings
                elif el.name == 'div':
                    p_string = (str(el))
                    p_string = remove_span_tags(p_string)
                    p_cleaner = (r'<p.*>|<\/p?>')
                    cleaned_string = re.sub(p_cleaner,'', p_string)
                    cleaned_string = remove_span_tags(cleaned_string)
                    cleaned_string = cleaned_string.replace('"',"")
                    if is_nonempty_string(cleaned_string):
                        section_content_for_slide.append(sc.Text(text=cleaned_string,style=TextStyles.PARAGRAPH))

            except Exception as ex:
                print('Section that caused error and was not added')
                print(ex)
        story_sidecar.add_slide(contents=section_content_for_slide, media=slide_media)
    new_storymap.cover(title="",summary="", by_line="")
    new_storymap._properties = replace_single_quotes(new_storymap._properties)
    new_storymap._properties = remove_span_tags(new_storymap._properties)
    string_json = json.dumps(new_storymap.properties, ensure_ascii=False)
    new_storymap.save()
    #---------------------------------------------------------
    # Clean up Map Settings - Sets Scale, Extent and Layer visibility
    #---------------------------------------------------------
    for map in map_setting_dict:
        # due to a recursive map media issue, save and load the story for each map
        new_storymap = StoryMap(new_storymap._itemid)
        story_sidecar = new_storymap.get(sidecar_id)
        map_node = story_sidecar.get(map)
        # Get Map Layers from resource ID
        map_id = new_storymap._properties['resources'][map_node.resource_node]['data']['itemId']
        map_webapp = gis_conn.content.get(map_id)
        map_instance = WebMap(map_webapp)
        layers = map_instance.layers
        new_storymap._properties['nodes'][map_node.node]['data']['mapLayers'] = [{"id":layer.id, "title":layer.title, "visible":layer.visibility} for layer in layers if "visibility" in layer]
        map_node.set_viewpoint(map_setting_dict[map]['map_extent'], map_setting_dict[map]['scale'])
        #Handle Layers
        if map_setting_dict[map].get('layers'):
            classic_layer_settings = {layer['id']:layer['visibility'] for layer in map_setting_dict[map].get('layers')}
            for index, layer in enumerate(new_storymap._properties['nodes'][map_node.node]['data']['mapLayers']):
                if layer['id'] in classic_layer_settings:
                    if classic_layer_settings[layer['id']]:
                        map_node.properties['node_dict']['data']['mapLayers'][index]['visible'] = True
                else:
                    for c_layer in classic_layer_settings:
                        if c_layer.startswith(layer['id']):
                            map_node.properties['node_dict']['data']['mapLayers'][index]['visible'] = True
        #Remove zoom and center props to allow for correct extent calculation in ArcGIS StoryMaps
        if map_node.properties['node_dict']['data'].get('zoom'):
            map_node.properties['node_dict']['data'].pop('zoom')
        if map_node.properties['node_dict']['data'].get('center'):
            map_node.properties['node_dict']['data'].pop('center')
        new_storymap.save()

    #---------------------------------------------------------
    # Clean up Resources - Removes Non-Essential Map Resource Data and Adds Theme
    #---------------------------------------------------------
    for resource in new_storymap._properties['resources']:
        if new_storymap._properties['resources'][resource]['type'] == 'webmap':
            new_storymap._properties['resources'][resource]['data']['type'] = 'minimal'
            new_storymap._properties['resources'][resource]['data'].pop('zoom', None)
            new_storymap._properties['resources'][resource]['data'].pop('center', None)
            new_storymap._properties['resources'][resource]['data'].pop('viewpoint', None)
            new_storymap._properties['resources'][resource]['data'].pop('mapLayers', None)
            new_storymap._properties['resources'][resource]['data'].pop('extent', None)
        elif new_storymap._properties['resources'][resource]['type'] == 'story-theme':
            print("Setting Theme Resource To: ")
            if theme_id not in ["summit","obsidian","mesa","ridgeline","tidal","slate"]:
                print("Org Supplied")
                new_storymap._properties['resources'][resource]['data']["themeItemId"] = theme_id
            else:
                print("App Theme")
                new_storymap._properties['resources'][resource]['data']["themeId"] = theme_id
        new_storymap.save()
    #---------------------------------------------------------
    # Clean up Embeds - Apply Card/Inline keywords and embedlyType
    #---------------------------------------------------------
    for embed in embed_settings_dict:
        embed_node = story_sidecar.get(embed)
        embed_node.properties['node_dict']['data']['embedType'] = embed_settings_dict[embed]['embedly_type']
        if embed_settings_dict[embed].get('display',None):
            embed_node.properties['node_dict']['data']['display'] = embed_settings_dict[embed]['display']

        embed_node.properties['node_dict']['data']['isEmbedSupported'] = True

    #---------------------------------------------------------
    # Remove Local Image versions
    #---------------------------------------------------------
    for image in local_images:
        os.remove(image)
    #---------------------------------------------------------
    # Remove Empty Slides - created by initial copy
    #---------------------------------------------------------
    new_storymap._properties['nodes'][sidecar_id]['children'].remove(slide_)
    #---------------------------------------------------------
    # Add Title to Item and Story Cover
    #---------------------------------------------------------
    new_storymap._item.title = "(COPY) " + journal_title
    new_storymap.cover(title="(COPY) " + journal_title)
    #---------------------------------------------------------
    # Final Save
    #---------------------------------------------------------
    try:
        new_storymap._item.typeKeywords.append('smconverted:converter-v2')
    except Exception as ex:
        pass
    new_storymap.save(publish=False)

    print("Conversion Done - please check your ArcGIS StoryMaps content")
    print(new_storymap._url)

def convert_cascade(itemid, theme_id="summit"):
    """
    Main function for notebook, This takes a story ID for a classic Cascade Storymap and creates a ArcGIS StoryMap with the content of the classic story in the logged in User's account

    Args:
        classic_story_id (string): string id of classic story

    Returns:
        string: URL or local path for image
    """

    #---------------------------------------------------------
    # Define private functions
    #---------------------------------------------------------
    def process_section(section:dict, storymap:StoryMap):
        sectiontype = section.get('type')
        if sectiontype == 'cover':
        #---------------------------------------------------------
        # Handle Cover information and image
        #---------------------------------------------------------
            has_image = False
            title = "(COPY)" + section['foreground'].get('title')
            subtitle = section['foreground'].get('subtitle')
            cover_media_type = section['background'].get('type')
            if cover_media_type == 'image':
                has_image = True
                cover_media = section['background']['image'].get('url')
                cover_media = process_img_tag(cover_media)
                cover_image = sc.Image(path=cover_media)
                storymap.cover(image=cover_image)
            if cover_media_type == 'video':
                # Print warning that video covers are not supported in the current version of the python API
                print("Video covers are not supported in the current version of the python API, this would need to be added manually after conversion")
            if has_image:
                storymap.cover(title=title,summary=subtitle,image=cover_image)
            else:
                storymap.cover(title=title,summary=subtitle)
            storymap._item.title = title
        if sectiontype == 'sequence':
        #---------------------------------------------------------
        # Handle Sequence information for narartive blocks text,image, video, embed and maps
        #---------------------------------------------------------
            section_blocks = section['foreground'].get('blocks')
            for block in section_blocks:
                process_block(block,storymap)
        if sectiontype == 'immersive':
            handle_immersive_section(section,storymap)
        if sectiontype == 'title':
            #Get title Text
            title = section['foreground'].get('title')
            #Get title Image
            if section['background'].get('type') == 'image':
                title_has_image = True
                title_image_url = section['background']['image'].get('url')
                title_image = process_img_tag(title_image_url)
            else:
                title_has_image = False
            #Add title to story
            text_content = sc.Text(text=title,style=TextStyles.HEADING)
            text_node_id = storymap.add(text_content)
            text_node = storymap.get(text_node_id)
            text_node.properties['node_dict']['data']['textAlignment'] = 'center'
            if title_has_image:
                # add image to the story with properties set to float
                image_content = sc.Image(path=title_image)
                image_content.display = 'float'
                image_node_id = storymap.add(image_content)
                image_node = storymap.get(image_node_id)
                image_node.properties['node_dict']['config']['size'] = 'float'
                image_node.properties['node_dict']['config']['floatAlignment'] = 'start'

            else:
                storymap.add(sc.Separator())
        if sectiontype == 'credits':
            handle_credit_section(section,storymap)

        #---------------------------------------------------------
        # Handle Immersive information and convert to SideCar
        #---------------------------------------------------------

    def add_link_to_text(text, href):
        #Required by the credit section to add links to the attribution text
        linked_text = f'<a href="{href}" rel="noopener noreferrer" target="_blank">{text}</a>'
        return linked_text
    def get_layers (webmapid):
        # Get all layers in a web map or web scene
        map_webapp = gis_conn.content.get(webmapid)
        if map_webapp.type.lower() == "web map":
            webapp_layers = WebMap(map_webapp).layers
        if map_webapp.type.lower() == "web scene":
            webapp_layers = WebScene(map_webapp).layers
        return webapp_layers
    def get_viewpoint(extent):
        # return the viewpoint and zoom level for a given extent
        map_scale, map_zoom = determine_scale_zoom_level(extent)
        if map_scale is None:
            return None, None
        viewpoint = {
            "targetGeometry": extent,
            "scale": map_scale
        }
        return viewpoint, map_zoom


    def fix_webmap_props(node_visibility_dict, map_resources_dict, map_extents, storymap):
        #For immersive blocks the properties of the webmap needs to be corrected to reflect the settings that was captured from the cascade item
        #This function takes the settings captured and updates the webmap properties
        #Also removes superfluous properties from the webmap resource
        for node_id, layer_list in node_visibility_dict.items():
            if layer_list is not None:
                modified_layerlist = [{"id":obj['id'], "visible":obj['visibility']} for obj in layer_list if obj is not None]
                if modified_layerlist != []:
                    storymap.properties['nodes'][node_id]['data']['mapLayers'] = modified_layerlist
                map_resource = storymap.properties['nodes'][node_id]["data"]["map"]
                map_resource_subtype = storymap.properties['resources'][map_resource]['data'].get('itemType')
                node_type = storymap.properties['nodes'][node_id]["type"]
                map_id = storymap.properties['resources'][map_resource]['data']['itemId']
                node_webmap_layers = get_layers(map_id)
                for layer in node_webmap_layers:
                    if layer.id not in [layer['id'] for layer in modified_layerlist]:
                        modified_layerlist.append({"id":layer.id, "title":layer.title, "visible":layer.visibility})

            if node_id in map_extents:
                map_extent = map_extents[node_id]
                if map_extent is not None:
                    storymap.properties['nodes'][node_id]['data']['extent'] = map_extent
            viewpoint, map_zoom = get_viewpoint(map_extent)
            if viewpoint is not None and node_type != 'Web Scene':
                storymap.properties['nodes'][node_id]['data']['viewpoint'] = viewpoint
                storymap.properties['nodes'][node_id]['data']['zoom'] = map_zoom
        for resource_id in map_resources_dict:
            storymap.properties['resources'][resource_id]['data']['type'] = 'minimal'
            if 'zoom' in storymap.properties['resources'][resource_id]['data']:
                storymap.properties['resources'][resource_id]['data'].pop('zoom')
            if 'center' in storymap.properties['resources'][resource_id]['data']:
                storymap.properties['resources'][resource_id]['data'].pop('center')
            if 'viewpoint' in storymap.properties['resources'][resource_id]['data']:
                storymap.properties['resources'][resource_id]['data'].pop('viewpoint')
            if 'mapLayers' in storymap.properties['resources'][resource_id]['data']:
                storymap.properties['resources'][resource_id]['data'].pop('mapLayers')
            if 'extent' in storymap.properties['resources'][resource_id]['data']:
                storymap.properties['resources'][resource_id]['data'].pop('extent')
        storymap.save()

    def handle_immersive_section(section:dict, storymap:StoryMap):
        # Handle Immersive information and convert to SideCar with the floating panel layout
        immersive_title = ""
        title_added = False
        side_car_id, slide_node_id, _ = add_empty_sidecar(storymap, type="floating-panel")
        new_sidecar = storymap.get(side_car_id)

        immersive_views = section['views']
        side_car_map_layer_visibility = {}
        side_car_map_extent = {}
        side_car_map_resources = {}
        side_car_map_viewpoints = {}
        for view in immersive_views:
            slide_media_type = view['background']['type']
            if slide_media_type == 'image':
                slide_media = view['background']['image'].get('url')
                slide_media = process_img_tag(slide_media)
                slide_media_content = sc.Image(path=slide_media)
            if slide_media_type in ['video','webpage']:
                slide_media = view['background'][slide_media_type].get('url')
                if slide_media.startswith ("/") == True and slide_media.startswith("//") == False:
                    slide_media = "https://example.com/"
                if slide_media.startswith("//") == False and slide_media.startswith("https://") == False and slide_media.startswith("/") == False:
                    slide_media = "https://example.com/"
                if slide_media.startswith("//") == True:
                    slide_media = "https:" + slide_media
                slide_media_content = sc.Embed(path=slide_media)
            if slide_media_type == 'webmap':
                slide_media = view['background']['webmap'].get('id')
                map_layers = view['background']['webmap'].get('layers')
                map_extent = view['background']['webmap'].get('extent')
                slide_media_content = sc.Map(item=slide_media)
                map_node_id = slide_media_content.node
                map_resource_id = slide_media_content.resource_node
                side_car_map_layer_visibility[map_node_id] = map_layers
                side_car_map_extent[map_node_id] = map_extent
                side_car_map_resources[map_resource_id] = {}
            if slide_media_type == 'webscene':
                slide_media = view['background']['webscene'].get('id')
                map_layers = view['background']['webscene'].get('layers')
                map_extent = view['background']['webscene'].get('extent')
                slide_media_content = sc.Map(item=slide_media)
                map_node_id = slide_media_content.node
                map_resource_id = slide_media_content.resource_node
                side_car_map_layer_visibility[map_node_id] = map_layers
                side_car_map_extent[map_node_id] = map_extent
                side_car_map_resources[map_resource_id] = {}
            if view['foreground'].get('title') != None:
                immersive_title = view['foreground']['title'].get('value','')
            narrative_content_list = []
            for panel in view['foreground']['panels']:
                for block in panel['blocks']:
                    narrative_content = process_block(block,storymap,return_as_content=True,layer_list=side_car_map_layer_visibility,map_extent=side_car_map_extent,map_resource_list=side_car_map_resources)
                    if title_added == False:
                        if immersive_title != "" or immersive_title is not None :
                            title_added = True
                            narrative_content_list.append(sc.Text(text=immersive_title,style=TextStyles.HEADING))
                    narrative_content_list.append(narrative_content)
            new_slide = new_sidecar.add_slide(contents=narrative_content_list, media=slide_media_content)
            slide_list = new_sidecar.properties
            latest_slide = slide_list[-1]
            fix_webmap_props(side_car_map_layer_visibility,side_car_map_resources,side_car_map_extent,storymap)
        new_storymap._properties['nodes'][side_car_id]['children'].pop(0)

    def handle_credit_section(section:dict, storymap:StoryMap):
        #Temporary early return until credit bug fix is available in July Release
        return

        # Handle credit information in the cascade. Adds credit description to the storymap as well as any attributions
        #Attributions get the link added inline
        credit_description = section['foreground']['panels'][0]['blocks'][0]
        credit_description_content = handleTextBlock(credit_description,storymap,return_as_string=True)
        #fix for python API bug to be fixed in mid 2023 release
        storymap_nodes = storymap._properties['nodes']
        found_credits = False
        for nodeid, node in storymap_nodes.items():
            if node['type'] == 'credits':
                found_credits = True
                storymap._properties['nodes'][nodeid]['children'] = []
        if found_credits == False:
            storymap._properties['nodes'][storymap._properties['root']]['children'].append("n-BWRGem")
            storymap._properties['nodes']['n-BWRGem'] = {
                "type": "credits",
                "children": []
            }
        print(storymap.get("credits"))
        storymap.credits(description=credit_description_content)
        attributions = section['foreground']['panels'][1]['credits']
        for attribution_object in attributions:
            content = attribution_object['label']
            attribution = attribution_object['source']
            if attribution_object['link'] != "":
                link = attribution_object['link']
                attribution = add_link_to_text(attribution,link)
                attribution = attribution.replace('"','')
            storymap.credits(content=content, attribution=attribution)

    def handleTextBlock(block:dict, storymap:StoryMap, **kwargs):
        #Text blocks are added to the storymap as text nodes
        #The Style and alignments are determined by the mappping
        #A bug exists for conversion of links in the text blocks, links are dropped when uploaded to AGO
        #TODO: Fix link bug
        def remove_color_span(text_soup):
            for spans in text_soup.find_all('span'):
                for span in spans:
                    if isinstance(span, Tag) and span.get('style') is not None and 'color' in span.get('style'):
                        if 'color' in span.get('style'):
                            span.unwrap()
            return text_soup
        def replace_linebreaks(text_soup):
            for br in text_soup.find_all("br"):
                br.replace_with("\n")
            return text_soup

        if 'return_as_content' in kwargs:
            return_as_content = kwargs.get('return_as_content')
        else:
            return_as_content = False
        if 'return_as_string' in kwargs:
            return_as_string = kwargs.get('return_as_string')
        else:
            return_as_string = False
        text_soup = BeautifulSoup(block['text'].get('value'),'html.parser')
        outermost_tag = text_soup.find(recursive=False)
        outermost_tag = remove_color_span(outermost_tag)
        outermost_tag = replace_linebreaks(outermost_tag)
        outermost_tag_name = outermost_tag.name
        if outermost_tag_name == 'p':
            style_attr = outermost_tag.get('style')
            if style_attr is not None:
                alignment_style_groups = re.search(r'text-align:\s*([^;]+)', style_attr)
                if alignment_style_groups is not None:
                    alignment_style = alignment_style_groups.group(1).strip()
                    alignment = alignmentMapping.get(alignment_style)
                else: alignment = alignmentMapping.get('left')
            else:
                alignment = alignmentMapping.get('left')

        else:
            alignment = 'center'
        text_type = textStyleMapping.get(outermost_tag_name)
        #remove remaining styling options in outermost tag
        del(outermost_tag['style'])
        #remove outermost p tag to allow viewing in StoryMaps
        if outermost_tag_name == 'p':
            outermost_tag.unwrap()
            outermost_string = text_soup
        else:
            outermost_string = outermost_tag
        replacement_dict = {'b':'strong','i':'em'}
        for key, value in replacement_dict.items():
            for tag in outermost_string.find_all(key):
                new_tag = text_soup.new_tag(value)
                for content in tag.contents:
                    new_tag.append(content)
                #new_tag.string = tag.text
                tag.replace_with(new_tag)
        outermost_string = str(outermost_string)
        outermost_string = outermost_string.replace('"','')
        text_content = sc.Text(text=outermost_string,style=text_type)
        if return_as_content == True:
            return text_content
        if return_as_string == True:
            return str(outermost_tag)
        new_text_node_id = storymap.add(text_content)
        new_text_node = storymap.get(new_text_node_id)
        new_text_node.properties['node_dict']['data']['textAlignment'] = alignment

        return new_text_node
        #{'node_dict': {'type': 'text', 'data': {'type': 'paragraph', 'text': 'Right Paragraph'}}}

        #print(text_node)
        #print(outermost_tag_name,text_type, alignment)

    def handle_embed_blocks(block:dict, storymap:StoryMap,**kwargs):
        # Embed blocks are added to the storymap
        # Both Video and Embed blocks from Cascade are converted to AGSM Embed blocks
        # This handles protocol neutral links and adds https:// to the url
        if 'return_as_content' in kwargs:
            return_as_content = kwargs.get('return_as_content')
        else:
            return_as_content = False
        embed_type = block['type']
        embed_url = block[embed_type]['url']
        if embed_url.startswith('https://') == False:
            embed_url = 'https://' + embed_url
        if embed_url.startswith('//'):
            embed_url = 'https:' + embed_url
        if embed_url.startswith('https://') == False:
            embed_url = "https://example.com/"
        if return_as_content == True:
            if embed_type == 'webpage':
                embed_content = sc.Embed(path=embed_url)
            elif embed_type == 'video':
                embed_content = sc.Embed(path=embed_url)
            return embed_content
        if embed_type == 'webpage':
            embed_node_id = storymap.add(sc.Embed(path=embed_url))
        elif embed_type == 'video':
            embed_node_id = storymap.add(sc.Embed(path=embed_url))
        embed_node = storymap.get(embed_node_id)
        if block[embed_type].get('caption') is not None:
            embed_node.caption = block[embed_type].get('caption')
        if block[embed_type].get('altText') is not None:
            embed_node.alt_text = block[embed_type].get('altText')

    def handle_image_blocks(block:dict, storymap:StoryMap, **kwargs):
        # Add image block to the AGSM story
        # This funtion also takes resource links in AGO and creates specific image resources associated with the AGSM item, in order to preserve the image even if the cascade item is deleted in the future
        if block.get('image') is not None:
            if 'return_as_content' in kwargs:
                return_as_content = kwargs.get('return_as_content')
            else:
                return_as_content = False
            image_media_url = block['image'].get('url')
            image_media = process_img_tag(image_media_url)
            if return_as_content == True:
                image_content = sc.Image(path=image_media)
                return image_content
            image_node_id = storymap.add(sc.Image(path=image_media))
            image_node = storymap.get(image_node_id)
            if block['image'].get('caption') is not None:
                image_node.caption = block['image'].get('caption').replace('"','')
            if block['image'].get('altText') is not None:
                image_node.alt_text = block['image'].get('altText')
        elif block.get('url') is not None:
            image_media_url = block['url']
            image_media = process_img_tag(image_media_url)
            image_node = sc.Image(path=image_media)
            return image_node

    def handle_gallery_block(block:dict, storymap:StoryMap, **kwargs):
        # Add image gallery block to the AGSM story
        images = block['image-gallery']['images']
        gallery_caption = block['image-gallery'].get('caption')
        gallery_alt = block['image-gallery'].get('altText')
        image_node_list = []
        for image in images:
            media_node = handle_image_blocks(image,storymap)
            image_node_list.append(media_node)
        new_gallery = sc.Gallery()
        storymap.add(new_gallery)
        new_gallery.add_images(image_node_list)
        if gallery_caption is not None:
            new_gallery.caption=block['image-gallery']['caption']
        if gallery_alt is not None:
            new_gallery.alt_text=block['image-gallery']['altText']

    def handle_webscene_block(block:dict, storymap:StoryMap, **kwargs):
        # Handle webscene blocks
        # capture layers visiblity and extent when possible
        if 'return_as_content' in kwargs:
            return_as_content = kwargs.get('return_as_content')
        else:
            return_as_content = False
        webscene_id = block['webscene']['id']
        if return_as_content == True:
            webscene_content = sc.Map(item=webscene_id)
            webscene_content_id = webscene_content.node
            if 'layer_list' in kwargs:
                webmap_layer_list = block['webmap'].get('layers')
                layer_list = kwargs.get('layer_list')
                layer_list[webscene_content_id] = webmap_layer_list
            if 'map_extent' in kwargs:
                webmap_extent = block['webmap'].get('extent')
                map_extent = kwargs.get('map_extent')
                map_extent[webscene_content_id] = webmap_extent
            if 'map_resource_list' in kwargs:
                map_resource_list = kwargs.get('map_resource_list')
                map_resource_list[webscene_content.resource_node] = {}
            return webscene_content
        webscene_caption = block['webscene'].get('caption')
        layer_list = block['webscene'].get('layers')
        webscene_node_id = storymap.add(sc.Map(item=webscene_id))
        webscene_node = storymap.get(webscene_node_id)
        webscene_resource_id = storymap.properties['nodes'][webscene_node_id]['data']['map']
        webscene_id = storymap.properties['resources'][webscene_resource_id]['data']['itemId']
        layers_from_web = get_layers(webscene_id)
        if layer_list is not None:
            modified_layer_list = [{'id':layer['id'],'title':layer['title'],'visible':False}for layer in layer_list]
            for layer in layers_from_web:
                if layer.id not in [layer['id'] for layer in modified_layer_list]:
                    modified_layer_list.append({'id':layer.id,'title':layer.title,'visible':layer.visibility})
            webscene_node.properties['node_dict']['data']['mapLayers'] = modified_layer_list
        extent = block['webscene'].get('extent')
        if extent is not None and extent != 'Null':
            viewpoint, zoom = get_viewpoint(extent)
            #if viewpoint is not None:
            #    storymap.properties['nodes'][webscene_node_id]['data']['viewpoint'] = viewpoint
            #    storymap.properties['nodes'][webscene_node_id]['data']['zoom'] = zoom
            storymap.properties['nodes'][webscene_node_id]['data']['extent'] = extent
        if webscene_caption is not None:
            webscene_node.caption = webscene_caption
        if block['webscene'].get('altText') is not None:
            webscene_node.alt_text = block['webscene'].get('altText')

    def handle_webmap_block(block:dict, storymap:StoryMap, **kwargs):
        #handle webmap blocks
        # capture layers visiblity and extent when possible
        webmap_id = block['webmap']['id']
        if 'return_as_content' in kwargs:
            return_as_content = kwargs.get('return_as_content')
        else:
            return_as_content = False
        if return_as_content == True:
            webmap_content = sc.Map(item=webmap_id)
            webmap_content_id = webmap_content.node
            if 'layer_list' in kwargs:
                webmap_layer_list = block['webmap'].get('layers')
                layer_list = kwargs.get('layer_list')
                layer_list[webmap_content_id] = webmap_layer_list
            if 'map_extent' in kwargs:
                webmap_extent = block['webmap'].get('extent')
                map_extent = kwargs.get('map_extent')
                map_extent[webmap_content_id] = webmap_extent
            if 'map_resource_list' in kwargs:
                map_resource_list = kwargs.get('map_resource_list')
                map_resource_list[webmap_content.resource_node] = {}
            return webmap_content
        webmap_node_id = storymap.add(sc.Map(item=webmap_id))
        webmap_node = storymap.get(webmap_node_id)
        webmap_caption = block['webmap'].get('caption')
        layer_list = block['webmap'].get('layers')
        webmap_resource_id = storymap.properties['nodes'][webmap_node_id]['data']['map']
        webmap_id = storymap.properties['resources'][webmap_resource_id]['data']['itemId']
        layers_from_web = get_layers(webmap_id)
        if layer_list is not None:
            modified_layer_list = [{'id':layer['id'],'title':layer['title'],'visible':False}for layer in layer_list]
            for layer in layers_from_web:
                if layer.id not in [layer['id'] for layer in modified_layer_list]:
                    modified_layer_list.append({'id':layer.id,'title':layer.title,'visible':layer.visibility})
            webmap_node.properties['node_dict']['data']['mapLayers'] = modified_layer_list
        extent = block['webmap'].get('extent')
        if extent is not None and extent != 'Null':
            viewpoint, zoom = get_viewpoint(extent)
            if viewpoint is not None:
                storymap.properties['nodes'][webmap_node_id]['data']['viewpoint'] = viewpoint
                storymap.properties['nodes'][webmap_node_id]['data']['zoom'] = zoom
            storymap.properties['nodes'][webmap_node_id]['data']['extent'] = extent
        if webmap_caption is not None:
            webmap_node.caption = webmap_caption
        if block['webmap'].get('altText') is not None:
            webmap_node.alt_text = block['webmap'].get('altText')

    def process_block(block:list, storymap:StoryMap, **kwargs):
        # Process the different block types found and convert them to the equivalent blocks in AGSM
        return_as_content = kwargs.get('return_as_content',False)
        blocktype = block.get('type')
        #print(block)
        if blocktype == 'text':
            block_content = handleTextBlock(block,storymap, return_as_content=return_as_content)
        if blocktype in ['video','webpage']:
            block_content = handle_embed_blocks(block,storymap, return_as_content=return_as_content)
        if blocktype == 'image':
            block_content = handle_image_blocks(block,storymap, return_as_content=return_as_content)
        if blocktype == 'image-gallery':
            block_content = handle_gallery_block(block,storymap, return_as_content=return_as_content)
        if blocktype == 'webscene':
            block_content = handle_webscene_block(block,storymap, return_as_content=return_as_content)
        if blocktype == 'webmap':
            block_content = handle_webmap_block(block,storymap, return_as_content=return_as_content)
        if return_as_content == True:
            if block_content is not None:
                return block_content
    #---------------------------------------------------------
    # Set Method Attributes
    #---------------------------------------------------------
    type_dict = {
    'image': sc.Image,
    'video': sc.Video,
    'embed': sc.Embed,
    'webmap': sc.Map
    }

    """
    Due to the need to add nodes to a story first and then update properties,
    properties/settings are tracked in the following dictionaries to be used to update the story at the end of the run
    """
    map_setting_dict = {} #Tracking dictionary for map settings
    embed_settings_dict = {}#Tracking dictionary for embeds
    image_settings_dict = {}#Tracking dictionary for images
    """Track locally created stories for deletion"""
    local_images = [] #Tracking dictionary for uploaded images

    #---------------------------------------------------------
    # Get StoryMap that has an empty Sidecar to copy
    #---------------------------------------------------------
    """For the current version of python a empty sidecar needs to be copied from a story.
    This can be removed and replaced with a created sidecar be updated post v2.1.0.2"""
    new_storymap = StoryMap()
    #---------------------------------------------------------
    #Get Classic StoryMap and data for conversion
    #---------------------------------------------------------
    classic_item = Item(gis=gis_conn,itemid=itemid)
    classic_keywords = classic_item.typeKeywords
    journal_title = classic_item.title

    # Determine the Classic type to allow for slight data model differences to be addressed later. Raise exception if not Journal or Series
    if 'Cascade'or 'cascade' in classic_keywords:
        classic_type = 'cascade'
    else:
        raise Exception('Sorry this code only support MapJournal and MapSeries Classic StoryMaps')

    classic_item_data = classic_item.get_data()
    try:
        classic_theme = classic_item_data['values']['settings']['theme']['colors']['themeMajor']
        if classic_theme == 'dark':
            theme_id = 'obsidian'
        elif classic_theme == 'light':
            theme_id = 'summit'
    except:
        print('no internal theme set in the cascade, using script setting')

    #---------------------------------------------------------
    # Loop Through classic sections and add content
    #---------------------------------------------------------

    classic_sections = classic_item_data['values'].get('sections',None)
    print(f"Converting {journal_title}")
    if classic_sections is None:
        raise Exception('Sorry this Cascade seems to be empty')
    for section in classic_sections:
        process_section(section, new_storymap)
    #---------------------------------------------------------
    # Remove images created during conversion
    #---------------------------------------------------------
    file_extentions = ['.jpg','.png','.gif','.jpeg']
    file_extentions.extend([extention.upper() for extention in file_extentions])
    files_to_remove = []
    for extention in file_extentions:
        files_to_remove.extend(glob.glob(f'*{extention}'))
    for file_path in files_to_remove:
        os.remove(file_path)
    #---------------------------------------------------------
    # Set Theme Resource
    #---------------------------------------------------------
    for resource_id in new_storymap._properties['resources']:
        if new_storymap._properties['resources'][resource_id]['type'] == 'story-theme':
            if theme_id not in ["summit","obsidian","mesa","ridgeline","tidal","slate"]:
                new_storymap._properties['resources'][resource_id]['data']["themeItemId"] = theme_id
            else:
                new_storymap._properties['resources'][resource_id]['data']["themeId"] = theme_id
    try:
        new_storymap._item.typeKeywords.append('smconverted:converter-v2')
    except Exception as ex:
        pass
    new_storymap.save()
    print("Conversion Done - please check your ArcGIS StoryMaps content for the Draft Story")
    print(new_storymap._url)

def convert_classic(itemid, theme_id='summit'):
    classic_journal_item = Item(gis=gis_conn,itemid=classic_story_id)
    classic_keywords = classic_journal_item.typeKeywords
    print(classic_keywords)
    # Determine the Classic type to allow for slight data model differences to be addressed later. Raise exception if not Journal or Series
    if 'MapJournal' in classic_keywords or 'mapjournal' in classic_keywords:
        classic_type = 'journal'
        print('converting Journal')
        convert_series_or_journal(itemid,theme_id=theme_id)
    elif 'MapSeries' in classic_keywords or 'mapseries' in classic_keywords:
        classic_type = 'series'
        print('converting Series')
        convert_series_or_journal(itemid,theme_id=theme_id)
    elif 'Cascade' in classic_keywords or 'cascade' in classic_keywords:
        classic_type = 'cascade'
        print('converting Cascade')
        convert_cascade(itemid,theme_id=theme_id)
    else:
        raise Exception('Sorry this code only support MapJournal,MapSeries and Cascade Classic StoryMaps')


if __name__ == "__main__":
    convert_classic(classic_story_id, theme_id=theme_id)
