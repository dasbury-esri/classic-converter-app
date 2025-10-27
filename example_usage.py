"""
Example Usage of Classic StoryMap Converters

This script demonstrates how to use both the API-based and JSON-to-JSON converters.
"""

import json

from converter_json import (JSONConverterFactory, cleanup_local_images,
                            convert_classic_to_json, save_json_to_file)

# =====================================================================
# Example 1: JSON-to-JSON Conversion (No API Required)
# =====================================================================

def example_json_conversion():
    """
    Example: Convert a classic story JSON file to StoryMap JSON

    This approach doesn't require the ArcGIS Python API or authentication.
    """
    print("=" * 70)
    print("Example 1: JSON-to-JSON Conversion")
    print("=" * 70)

    # Step 1: Load classic story JSON
    # (You would get this from the ArcGIS REST API or item.get_data())
    print("\n1. Loading classic story JSON...")

    # Example: Load from file
    # with open('classic_story.json', 'r', encoding='utf-8') as f:
    #     classic_json = json.load(f)

    # For this example, we'll create a minimal mock structure
    classic_json = {
        "values": {
            "title": "My Classic Journal",
            "story": {
                "sections": [
                    {
                        "title": "Introduction",
                        "content": "<p>Welcome to my story!</p>",
                        "media": {
                            "type": "webmap",
                            "webmap": {
                                "id": "abc123def456",
                                "extent": {
                                    "xmin": -180,
                                    "xmax": 180,
                                    "ymin": -90,
                                    "ymax": 90
                                }
                            }
                        }
                    }
                ]
            }
        }
    }

    print("   ✓ Classic story loaded")

    # Step 2: Convert to StoryMap JSON
    print("\n2. Converting to StoryMap JSON...")
    storymap_json = convert_classic_to_json(
        classic_json,
        theme_id="summit",
        gis_token=None  # Optional: for downloading AGO images
    )
    print("   ✓ Conversion complete")

    # Step 3: Validate
    print("\n3. Validating StoryMap JSON structure...")
    from storymap_json_schema import validate_storymap_json
    errors = validate_storymap_json(storymap_json)

    if errors:
        print("   ⚠ Validation errors found:")
        for error in errors:
            print(f"     - {error}")
    else:
        print("   ✓ JSON structure is valid")

    # Step 4: Save to file
    print("\n4. Saving to file...")
    save_json_to_file(storymap_json, 'example_output.json')
    print("   ✓ Saved to example_output.json")

    # Step 5: Show structure summary
    print("\n5. StoryMap structure summary:")
    print(f"   - Root node: {storymap_json['root']}")
    print(f"   - Total nodes: {len(storymap_json['nodes'])}")
    print(f"   - Total resources: {len(storymap_json['resources'])}")
    print(f"   - Node types: {set(node['type'] for node in storymap_json['nodes'].values())}")

    print("\n" + "=" * 70)
    print("JSON conversion complete!")
    print("=" * 70)
    print("\nNext steps:")
    print("1. Review example_output.json")
    print("2. Upload JSON to ArcGIS using REST API to create StoryMap item")
    print("3. Publish the new story")


# =====================================================================
# Example 2: API-Based Conversion
# =====================================================================

def example_api_conversion():
    """
    Example: Convert using the ArcGIS Python API

    This approach requires arcgis package and authentication.
    """
    print("\n" + "=" * 70)
    print("Example 2: API-Based Conversion")
    print("=" * 70)

    print("\nTo use the API-based converter:")
    print("\n1. Edit converter_v2.py configuration:")
    print("   classic_story_id = 'YOUR_ITEM_ID'")
    print("   theme_id = 'summit'")
    print("   username = 'your_username' (or leave empty for 'home' auth)")
    print("   password = 'your_password'")

    print("\n2. Run the converter:")
    print("   python converter_v2.py")

    print("\n3. The script will:")
    print("   - Fetch the classic story from ArcGIS")
    print("   - Create a new StoryMap with converted content")
    print("   - Save as unpublished draft in your content")
    print("   - Print the URL of the new story")

    print("\n" + "=" * 70)


# =====================================================================
# Example 3: Direct Converter Factory Usage
# =====================================================================

def example_factory_usage():
    """
    Example: Using the converter factory for automatic type detection
    """
    print("\n" + "=" * 70)
    print("Example 3: Using Converter Factory")
    print("=" * 70)

    # Example Journal
    journal_json = {
        "values": {
            "title": "My Journal",
            "story": {
                "sections": []
            }
        }
    }

    # Example Cascade
    cascade_json = {
        "values": {
            "title": "My Cascade",
            "sections": []
        }
    }

    print("\n1. Detecting story types...")

    # Factory automatically detects type
    journal_converter = JSONConverterFactory.get_converter(journal_json)
    cascade_converter = JSONConverterFactory.get_converter(cascade_json)

    print(f"   - Journal detected: {type(journal_converter).__name__}")
    print(f"   - Cascade detected: {type(cascade_converter).__name__}")

    print("\n2. Converting both types...")
    journal_result = journal_converter.convert()
    cascade_result = cascade_converter.convert()

    print("   ✓ Both conversions complete")

    print("\n" + "=" * 70)


# =====================================================================
# Example 4: Processing Classic JSON from REST API
# =====================================================================

def example_rest_api_workflow():
    """
    Example: Complete workflow using REST API
    """
    print("\n" + "=" * 70)
    print("Example 4: Complete REST API Workflow")
    print("=" * 70)

    print("\nWorkflow for JSON-to-JSON conversion with REST API:")

    print("\n1. Get classic story data:")
    print("   GET https://www.arcgis.com/sharing/rest/content/items/{itemId}/data")
    print("   Response: classic_json")

    print("\n2. Convert to StoryMap JSON:")
    print("   storymap_json = convert_classic_to_json(classic_json)")

    print("\n3. Create new StoryMap item:")
    print("   POST https://www.arcgis.com/sharing/rest/content/users/{username}/addItem")
    print("   Parameters:")
    print("     - type: 'StoryMap'")
    print("     - title: '(COPY) Original Title'")
    print("     - text: json.dumps(storymap_json)")

    print("\n4. Upload image resources:")
    print("   For each local image in storymap_json:")
    print("     POST https://www.arcgis.com/sharing/rest/content/users/{username}/items/{itemId}/addResources")

    print("\n5. Publish the story:")
    print("   POST https://www.arcgis.com/sharing/rest/content/users/{username}/items/{itemId}/publish")

    print("\n" + "=" * 70)


# =====================================================================
# Example 5: Batch Conversion
# =====================================================================

def example_batch_conversion():
    """
    Example: Converting multiple stories in batch
    """
    print("\n" + "=" * 70)
    print("Example 5: Batch Conversion")
    print("=" * 70)

    print("\nBatch processing multiple classic stories:")

    # Simulated list of story IDs
    story_ids = [
        "story1_itemid_here",
        "story2_itemid_here",
        "story3_itemid_here",
    ]

    print(f"\n1. Processing {len(story_ids)} stories...")

    for i, story_id in enumerate(story_ids, 1):
        print(f"\n   Story {i}/{len(story_ids)}: {story_id}")
        print("     - Fetching data from REST API...")
        print("     - Converting to JSON...")
        print("     - Validating...")
        print("     - Saving to file...")
        print("     ✓ Complete")

    print("\n2. All conversions complete!")
    print("   - Review output files")
    print("   - Upload to ArcGIS in batch")

    print("\n" + "=" * 70)


# =====================================================================
# Main
# =====================================================================

def main():
    """Run all examples"""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "Classic StoryMap Converter Examples" + " " * 18 + "║")
    print("╚" + "═" * 68 + "╝")

    # Run examples
    example_json_conversion()
    example_api_conversion()
    example_factory_usage()
    example_rest_api_workflow()
    example_batch_conversion()

    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 26 + "All Examples Complete" + " " * 21 + "║")
    print("╚" + "═" * 68 + "╝")
    print("\nFor more information, see:")
    print("  - README.md (overview and usage)")
    print("  - CONVERTER_LOGIC.md (detailed documentation)")
    print("  - CONVERTER_LOGIC_DIAGRAM.md (visual flowcharts)")
    print("  - IMPROVEMENTS.md (future enhancements)")
    print()


if __name__ == "__main__":
    main()

