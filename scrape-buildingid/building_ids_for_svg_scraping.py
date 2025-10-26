# python scrape-buildingid/building_ids_for_svg_scraping.py
# run this file to scrape floorIDs from html dump from FMSsystems website

import os
import json
import sys
from bs4 import BeautifulSoup
from building_codes_to_floor_ids import process_building_codes_directory
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from s3_utils import upload_json_file, upload_generic_file, get_json_from_s3, get_generic_file_from_s3, upload_folder, list_bucket_objects

def extract_buildings(buildings_file: str = "scrape-buildingid/building_names.html"):
    try:
        with open(buildings_file, 'r', encoding='utf-8') as file:
            html_content = file.read()
    except FileNotFoundError:
        print("buildings_file not found locally — fetching from S3")
        html_content = get_generic_file_from_s3("building_codes_htmls/building_names.html")

    try:
        with open("scrape-buildingid/building_abbrev_mappings.json", "r", encoding='utf-8') as file:
            mappings = json.load(file)
    except FileNotFoundError:
        print("mappings JSON file not found locally — fetching from S3")
        mappings = get_json_from_s3("building-utils/building_abbrev_mappings.json", return_data=True)
    
    soup = BeautifulSoup(html_content, "html.parser")
    
    links = soup.find_all("a", class_="rtIn")
    
    buildings = []
    for link in links:
        text = link.get_text(strip=True)
        # Remove trailing building code like "(012)"
        name = text.rsplit(" (", 1)[0]
        buildings.append(name)
    
    buildings_abbrev = []
    for building in buildings:
        found = False  # flag to track if we find a match
        building_lower = building.lower()
        for abbrev, info in mappings.items():
            name_lower = info["name"].lower()
            if name_lower in building_lower or building_lower in name_lower:
                found = True
                buildings_abbrev.append(abbrev)
                break
            elif "FMS_alias" in info:
                alias_lower = info["FMS_alias"].lower()
                if alias_lower in building_lower or alias_lower in name_lower:
                    found = True
                    buildings_abbrev.append(abbrev)
                    break
        if not found:
            print(f"not in mapping: {building}")
            buildings_abbrev.append(building)
    print(buildings_abbrev)
    return buildings_abbrev

def extract_htmls_from_txt(text_file: str, buildings: list[str], output_dir: str = "building_codes"):
    """
    Extract individual HTML segments from a large text file that contains
    multiple sections starting with lines beginning with 's['.

    Each section will be saved as a separate .html file named after the
    corresponding building in the `buildings` list.
    """
    os.makedirs(output_dir, exist_ok=True)
    try:
        with open(text_file, 'r', encoding='utf-8') as file:
            text_data = file.read()
    except FileNotFoundError:
        print("htmls text file not found locally — fetching from S3")
        text_data = get_generic_file_from_s3("building_codes_htmls/all_building_htmls.txt")
        text_data = text_data.read().decode('utf-8')

    # Replace each 's[' section start with a marker so we can split later
    # We'll detect lines that start with 's[' and insert a separator.
    new_lines = []
    for line in text_data.splitlines():
        if line.strip().startswith("s["):
            new_lines.append("BREAK_MARKER")
        new_lines.append(line)
    joined_text = "\n".join(new_lines)

    html_segments = [seg.strip() for seg in joined_text.split("BREAK_MARKER") if seg.strip()]

    if len(buildings) != len(html_segments):
        print(f"⚠️ Warning: {len(buildings)} buildings but {len(html_segments)} HTML sections found.")

    # Save each HTML segment into a file named after the building
    for building, content in zip(buildings, html_segments):
        safe_name = building.replace(" ", "_").replace("/", "-")
        output_path = os.path.join(output_dir, f"{safe_name}.html")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"Saved: {output_path}")

    return

def extract_all_htmls():
    buildings_file = "scrape-buildingid/building_names.html"
    text_file = "scrape-buildingid/all_building_htmls.txt"
    
    buildings = extract_buildings(buildings_file)
    extract_htmls_from_txt(text_file, buildings)

if __name__ == "__main__":
    list_bucket_objects()
    # extracts htmls and saves them to building_codes/ folder
    extract_all_htmls()
    
    # # saves all building codes to all_building_codes.json
    process_building_codes_directory()
    
    # upload_json_file("all_building_codes.json", "building-utils/all_building_codes.json")
    # upload_json_file("scrape-buildingid/building_abbrev_mappings.json", "building-utils/building_abbrev_mappings.json")
    # list_bucket_objects()