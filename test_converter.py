"""
Test Script for Classic StoryMap to JSON Converter

This script batch-processes all classic story JSON files in test_data/classics/
and converts them to new StoryMap JSON format using converter_json.py.

It then creates actual ArcGIS StoryMap items and replaces their .properties
with the converted JSON to verify the conversion works in the actual application.

Usage:
    python test_converter.py              # Convert and create StoryMap items
    python test_converter.py --json-only  # Only generate JSON files, don't create items
    python test_converter.py --analyze    # Analyze test data only
"""

import glob
import json
import os
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from converter_json import (JSONConverterFactory, cleanup_local_images,
                            convert_classic_to_json, save_json_to_file)
from storymap_json_schema import validate_storymap_json

# Try to import python-dotenv (optional - for .env file support)
try:
    from dotenv import load_dotenv
    load_dotenv()
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    # Will fall back to hardcoded values or environment variables

# Try to import ArcGIS API (optional - only needed for actual item creation)
try:
    from arcgis.apps.storymap import StoryMap
    from arcgis.gis import GIS
    ARCGIS_AVAILABLE = True
except ImportError:
    ARCGIS_AVAILABLE = False
    print("Warning: arcgis package not available. Running in JSON-only mode.")


# =====================================================================
# Configuration
# =====================================================================

INPUT_DIR = "test_data/classics"
OUTPUT_DIR = "test_data/output"
REPORT_FILE = "test_data/test_report.txt"

# ArcGIS configuration (for creating actual StoryMap items)
# Reads from .env file or environment variables
# Falls back to these defaults if not found
PORTAL = os.getenv("GIS_PORTAL", "https://www.arcgis.com")
USERNAME = os.getenv("GIS_USERNAME", "")
PASSWORD = os.getenv("GIS_PASSWORD", "")

# Connect to ArcGIS (if available)
gis_conn = None
if ARCGIS_AVAILABLE:
    try:
        if DOTENV_AVAILABLE:
            print("[OK] Loaded configuration from .env file")

        if USERNAME == "":
            print("  Using 'home' authentication...")
            gis_conn = GIS("home")
        else:
            print(f"  Connecting to {PORTAL}...")
            gis_conn = GIS(PORTAL, USERNAME, PASSWORD)

        print(f"[OK] Connected to ArcGIS as: {gis_conn.users.me.username}")
    except Exception as e:
        print(f"[WARN] Could not connect to ArcGIS: {e}")
        print("  Running in JSON-only mode")
        ARCGIS_AVAILABLE = False


# =====================================================================
# Test Functions
# =====================================================================

def detect_classic_type(classic_json: Dict[str, Any]) -> str:
    """
    Detect the classic story type from JSON structure

    Returns:
        'journal', 'series', or 'cascade'
    """
    values = classic_json.get('values', {})

    # Check for Journal/Series
    if 'story' in values:
        story = values['story']
        if 'sections' in story:
            # Check layout to distinguish Journal vs Series
            layout = values.get('settings', {}).get('layout', {}).get('id', '')
            if layout in ['tab', 'bullet']:
                return 'series'
            return 'journal'
        elif 'entries' in story:
            return 'series'

    # Check for Cascade
    if 'sections' in values:
        template_name = values.get('template', {}).get('name', '')
        if 'Cascade' in template_name:
            return 'cascade'
        # Even without template, sections in values indicates Cascade
        return 'cascade'

    return 'unknown'


def create_storymap_from_json(storymap_json: Dict[str, Any], title: str, local_images: List[str]) -> Optional[str]:
    """
    Create an actual ArcGIS StoryMap item with the converted JSON

    Args:
        storymap_json: Converted StoryMap JSON
        title: Title for the new story
        local_images: List of local image files to upload as resources

    Returns:
        StoryMap URL or None if failed
    """
    if not ARCGIS_AVAILABLE or gis_conn is None:
        return None

    try:
        print()  # New line for better formatting

        # Step 1: Create a new StoryMap
        print("    Creating base StoryMap...", end=" ")
        new_storymap = StoryMap()
        new_storymap._item.title = f"(TEST) {title}"
        new_storymap.save(publish=False)
        print("[OK]")

        # Step 2: Upload image resources BEFORE setting properties
        if local_images:
            print(f"    Uploading {len(local_images)} image(s)...", end=" ")
            for img_path in local_images:
                if os.path.exists(img_path):
                    try:
                        new_storymap._item.resources.add(img_path)
                    except Exception as img_err:
                        print(f"\n      [WARN] Could not upload {img_path}: {img_err}")
            print("[OK]")

        # Step 3: Replace properties with converted JSON
        print("    Replacing properties...", end=" ")
        new_storymap._properties = storymap_json
        print("[OK]")

        # Step 4: Add test tracking keyword
        print("    Adding keywords...", end=" ")
        try:
            new_storymap._item.typeKeywords.append('smconverted:json-test')
        except Exception:
            pass
        print("[OK]")

        # Step 5: Final save with new properties
        print("    Final save...", end=" ")
        new_storymap.save(publish=False)
        print("[OK]")

        return new_storymap._url

    except Exception as e:
        print(f"\n    [FAIL] Error creating StoryMap item:")
        print(f"       {type(e).__name__}: {e}")
        traceback.print_exc()
        return None


def test_single_file(input_path: str, output_path: str, create_item: bool = True) -> Dict[str, Any]:
    """
    Test conversion of a single classic story file

    Returns:
        Dictionary with test results
    """
    filename = os.path.basename(input_path)

    result = {
        'filename': filename,
        'input_path': input_path,
        'output_path': output_path,
        'status': 'pending',
        'classic_type': 'unknown',
        'error': None,
        'nodes_count': 0,
        'resources_count': 0,
        'validation_errors': [],
        'converter_type': 'unknown',
        'storymap_url': None,
        'title': 'Untitled'
    }

    try:
        # Load classic story JSON
        print(f"\nProcessing: {filename}")
        print("  Loading JSON...", end=" ")

        with open(input_path, 'r', encoding='utf-8') as f:
            classic_json = json.load(f)

        # Extract title for later use
        values = classic_json.get('values', {})
        if 'title' in values:
            result['title'] = values['title']
        elif 'story' in values and 'title' in values.get('story', {}):
            result['title'] = values['story']['title']

        # Check if file is empty or invalid
        if not classic_json or 'values' not in classic_json:
            result['status'] = 'skipped'
            result['error'] = 'Empty or invalid JSON file'
            print("SKIPPED (empty/invalid)")
            return result

        print("[OK]")

        # Detect classic type
        print("  Detecting type...", end=" ")
        classic_type = detect_classic_type(classic_json)
        result['classic_type'] = classic_type
        print(f"{classic_type.upper()}")

        if classic_type == 'unknown':
            result['status'] = 'failed'
            result['error'] = 'Unknown classic story type'
            print("  [FAIL] Failed: Unknown type")
            return result

        # Get converter
        print("  Getting converter...", end=" ")
        converter = JSONConverterFactory.get_converter(classic_json, theme_id="summit")
        result['converter_type'] = type(converter).__name__
        print(f"{result['converter_type']}")

        # Convert
        print("  Converting...", end=" ")
        storymap_json = converter.convert()
        result['nodes_count'] = len(storymap_json.get('nodes', {}))
        result['resources_count'] = len(storymap_json.get('resources', {}))
        print(f"[OK] ({result['nodes_count']} nodes, {result['resources_count']} resources)")

        # Validate
        print("  Validating...", end=" ")
        validation_errors = validate_storymap_json(storymap_json)
        result['validation_errors'] = validation_errors

        if validation_errors:
            print(f"[WARN] {len(validation_errors)} validation errors")
            for error in validation_errors[:3]:  # Show first 3
                print(f"    - {error}")
            if len(validation_errors) > 3:
                print(f"    ... and {len(validation_errors) - 3} more")
        else:
            print("[OK]")

        # Save output JSON
        print("  Saving JSON...", end=" ")
        save_json_to_file(storymap_json, output_path)
        print("[OK]")

        # Get local images BEFORE creating item (needed for upload)
        local_images = converter.get_local_images()

        # Create actual StoryMap item (if enabled)
        if create_item and ARCGIS_AVAILABLE and gis_conn:
            print("  Creating StoryMap item...")
            storymap_url = create_storymap_from_json(storymap_json, result['title'], local_images)

            if storymap_url:
                result['storymap_url'] = storymap_url
                print(f"  [OK] StoryMap created successfully!")
                print(f"    URL: {storymap_url}")
            else:
                print("  [FAIL] StoryMap creation failed (see errors above)")

        # Cleanup local images AFTER item creation
        print("  Cleaning up...", end=" ")
        for img in local_images:
            if os.path.exists(img):
                os.remove(img)
        print("[OK]")

        result['status'] = 'success'
        print(f"  [SUCCESS]")

    except Exception as e:
        result['status'] = 'failed'
        result['error'] = str(e)
        result['traceback'] = traceback.format_exc()
        print(f"  [FAIL] FAILED: {e}")

    return result


def generate_report(results: List[Dict[str, Any]], report_path: str, create_items: bool = True) -> None:
    """
    Generate and save detailed test report

    Args:
        results: List of test result dictionaries
        report_path: Path to save report file
    """
    report_lines = []

    # Header
    report_lines.append("=" * 70)
    report_lines.append("Classic StoryMap Converter - Test Report")
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("=" * 70)
    report_lines.append("")

    # Individual test results
    for i, result in enumerate(results, 1):
        report_lines.append(f"Test {i}: {result['filename']}")
        report_lines.append(f"  Type: {result['classic_type'].upper()}")
        report_lines.append(f"  Converter: {result['converter_type']}")
        report_lines.append(f"  Status: {result['status'].upper()}")

        if result['status'] == 'success':
            report_lines.append(f"  Nodes: {result['nodes_count']}")
            report_lines.append(f"  Resources: {result['resources_count']}")

            if result['validation_errors']:
                report_lines.append(f"  Validation: [WARN] {len(result['validation_errors'])} errors")
                for error in result['validation_errors'][:5]:
                    report_lines.append(f"    - {error}")
                if len(result['validation_errors']) > 5:
                    report_lines.append(f"    ... and {len(result['validation_errors']) - 5} more")
            else:
                report_lines.append(f"  Validation: [OK] Passed")

            report_lines.append(f"  Output: {result['output_path']}")

            if result.get('storymap_url'):
                report_lines.append(f"  StoryMap URL: {result['storymap_url']}")

        elif result['status'] == 'failed':
            report_lines.append(f"  Error: {result['error']}")
            if 'traceback' in result:
                report_lines.append(f"  Traceback:")
                for line in result['traceback'].split('\n')[:10]:
                    report_lines.append(f"    {line}")

        elif result['status'] == 'skipped':
            report_lines.append(f"  Reason: {result['error']}")

        report_lines.append("")

    # Summary
    report_lines.append("=" * 70)
    report_lines.append("Summary:")

    total = len(results)
    success = sum(1 for r in results if r['status'] == 'success')
    failed = sum(1 for r in results if r['status'] == 'failed')
    skipped = sum(1 for r in results if r['status'] == 'skipped')

    report_lines.append(f"  Total Tests: {total}")
    report_lines.append(f"  Success: {success}")
    report_lines.append(f"  Failed: {failed}")
    report_lines.append(f"  Skipped: {skipped}")

    if total > 0:
        success_rate = (success / total) * 100
        report_lines.append(f"  Success Rate: {success_rate:.1f}%")

    # Type breakdown
    report_lines.append("")
    report_lines.append("  By Type:")
    type_counts = {}
    for result in results:
        if result['status'] == 'success':
            classic_type = result['classic_type']
            type_counts[classic_type] = type_counts.get(classic_type, 0) + 1

    for story_type, count in sorted(type_counts.items()):
        report_lines.append(f"    {story_type.capitalize()}: {count}")

    # Validation summary
    total_validation_errors = sum(len(r['validation_errors']) for r in results)
    report_lines.append("")
    report_lines.append(f"  Total Validation Errors: {total_validation_errors}")

    report_lines.append("=" * 70)

    # Write report to file
    report_text = '\n'.join(report_lines)

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_text)

    # Also print to console
    print("\n" + report_text)


def run_all_tests(create_items: bool = True) -> None:
    """
    Main test runner - processes all classic story files

    Args:
        create_items: If True, create actual StoryMap items in ArcGIS
    """
    print("=" * 70)
    print("Classic StoryMap Converter - Test Suite")
    print("=" * 70)

    if create_items:
        if ARCGIS_AVAILABLE and gis_conn:
            print(f"Mode: Full conversion with ArcGIS item creation")
        else:
            print(f"Mode: JSON-only (ArcGIS not available)")
            create_items = False
    else:
        print(f"Mode: JSON-only (--json-only flag)")
    print()

    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"\nOutput directory: {OUTPUT_DIR}")

    # Find all JSON files in input directory
    pattern = os.path.join(INPUT_DIR, "*.json")
    input_files = glob.glob(pattern)

    print(f"Found {len(input_files)} test files in {INPUT_DIR}")

    if not input_files:
        print("No JSON files found!")
        return

    # Process each file
    results = []

    for input_path in sorted(input_files):
        filename = os.path.basename(input_path)
        output_path = os.path.join(OUTPUT_DIR, filename)

        result = test_single_file(input_path, output_path, create_item=create_items)
        results.append(result)

    # Generate report
    print("\n" + "=" * 70)
    print("Generating test report...")
    print("=" * 70)

    generate_report(results, REPORT_FILE, create_items)
    print(f"\nReport saved to: {REPORT_FILE}")

    # Quick summary
    success_count = sum(1 for r in results if r['status'] == 'success')
    total_count = len(results)

    print("\n" + "=" * 70)
    if success_count == total_count:
        print("[OK] ALL TESTS PASSED!")
    else:
        print(f"[WARN] {success_count}/{total_count} tests passed")
    print("=" * 70)


# =====================================================================
# Helper Functions
# =====================================================================

def analyze_classic_story(json_path: str) -> None:
    """
    Analyze a classic story JSON and print structure info

    Args:
        json_path: Path to classic story JSON file
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"\nAnalyzing: {os.path.basename(json_path)}")
    print("-" * 50)

    values = data.get('values', {})

    # Type detection
    classic_type = detect_classic_type(data)
    print(f"Type: {classic_type.upper()}")

    # Title
    title = values.get('title', 'No title')
    if classic_type in ['journal', 'series']:
        title = values.get('story', {}).get('title', title)
    print(f"Title: {title}")

    # Theme
    theme = values.get('settings', {}).get('theme', {}).get('colors', {}).get('themeMajor', 'N/A')
    print(f"Theme: {theme}")

    # Content count
    if classic_type in ['journal', 'series']:
        sections = values.get('story', {}).get('sections', [])
        entries = values.get('story', {}).get('entries', [])
        count = len(sections) + len(entries)
        print(f"Sections/Entries: {count}")
    elif classic_type == 'cascade':
        sections = values.get('sections', [])
        print(f"Sections: {len(sections)}")

        # Section types
        section_types = {}
        for section in sections:
            s_type = section.get('type', 'unknown')
            section_types[s_type] = section_types.get(s_type, 0) + 1

        print("Section breakdown:")
        for s_type, count in sorted(section_types.items()):
            print(f"  - {s_type}: {count}")

    print("-" * 50)


def analyze_all_test_data() -> None:
    """Analyze all test data files"""
    print("=" * 70)
    print("Test Data Analysis")
    print("=" * 70)

    pattern = os.path.join(INPUT_DIR, "*.json")
    input_files = glob.glob(pattern)

    for input_path in sorted(input_files):
        try:
            analyze_classic_story(input_path)
        except Exception as e:
            print(f"\nError analyzing {os.path.basename(input_path)}: {e}")

    print("\n" + "=" * 70)


# =====================================================================
# Main
# =====================================================================

def main():
    """Main entry point"""
    import sys

    create_items = True

    if len(sys.argv) > 1:
        if sys.argv[1] == '--analyze':
            # Just analyze, don't convert
            analyze_all_test_data()
            return
        elif sys.argv[1] == '--json-only':
            # Convert to JSON but don't create ArcGIS items
            create_items = False
        elif sys.argv[1] == '--help':
            print("Usage:")
            print("  python test_converter.py              # Convert and create StoryMap items")
            print("  python test_converter.py --json-only  # Generate JSON only, no ArcGIS items")
            print("  python test_converter.py --analyze    # Analyze test data only")
            print("  python test_converter.py --help       # Show this help")
            print()
            print("Note: Creating StoryMap items requires:")
            print("  - arcgis Python package installed")
            print("  - Valid ArcGIS authentication (create .env file or set environment variables)")
            print()
            print("Configuration:")
            print("  1. Create a .env file with:")
            print("     GIS_PORTAL=https://www.arcgis.com")
            print("     GIS_USERNAME=your_username")
            print("     GIS_PASSWORD=your_password")
            print("  2. Or set environment variables")
            print("  3. Or leave empty to use 'home' authentication")
            return

    # Run all tests
    run_all_tests(create_items=create_items)


if __name__ == "__main__":
    main()

