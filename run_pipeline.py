import os
import geojson

from svg_to_geojson_final import (
    load_svg, simplify_geojson, remove_duplicate_polygons,
    remove_covered_polygons, combine_overlapping_polygons, get_match_polygons
)
from bs4 import BeautifulSoup
import json
import uuid

def process_svg_to_geojson(svg_file_path):
    """Process SVG file and return GeoJSON data"""
    gj = load_svg(svg_file_path)
    gj = simplify_geojson(gj)
    gj = remove_duplicate_polygons(gj)
    gj = remove_covered_polygons(gj)
    gj = combine_overlapping_polygons(gj)
    feature_collection = get_match_polygons(svg_file_path, gj, strict=False)

    return feature_collection

def process_html_room_types(html_file_path, geojson_data):
    """Process HTML file to add room types to GeoJSON"""

    # Load your HTML file
    
    with open(html_file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    # Initialize dictionary for mapping
    room_map = {}

    # Find all spans with id ending in '_3' and '_4'
    spans_3 = soup.find_all("span", id=lambda x: x and x.endswith("_3"))
    spans_4 = soup.find_all("span", id=lambda x: x and x.endswith("_4"))

    # Iterate and extract mapping
    for room_span, name_span in zip(spans_3, spans_4):
        room_number = room_span.get_text(strip=True)
        room_name = name_span.get_text(strip=True)
        room_map[room_number] = room_name

    # Iterate over each feature in the GeoJSON
    for feature in geojson_data["features"]:
        # Get the room number from the feature's properties
        room_name = feature["properties"].get("room_name")

        # Find the room type using the room_map
        if room_name == "no_tag":
            room_type = ""
        else:
            room_type = room_map[room_name]

        # Add the room type to the feature's properties
        feature["properties"]["room_type"] = room_type

    return geojson_data

def process_geojson_to_json(geojson_data, base_name):
    """Convert GeoJSON to final JSON format"""

    rooms = dict()

    for feature in geojson_data["features"]:
        elements = dict()
        elements["name"] = feature["properties"]["room_name"]
        elements["labelPosition"] = dict()
        elements["labelPosition"]["longitude"] = feature["properties"]["labelPosition"][
            0
        ]
        elements["labelPosition"]["latitude"] = feature["properties"]["labelPosition"][
            1
        ]
        elements["type"] = feature["properties"]["room_type"]
        elements["id"] = str(uuid.uuid4())
        elements["coordinates"] = []
        elements["floor"] = dict()
        elements["floor"]["level"] = base_name.split("-")[1]
        
        for polygon in feature["geometry"]["coordinates"][0]:
            poly_cord = []
            p = dict()
            p["longitude"] = polygon[0]
            p["latitude"] = polygon[1]
            poly_cord.append(p)
            elements["coordinates"].append(poly_cord)
        rooms[elements["id"]] = elements

    output_file = os.path.join("output_files", f"{base_name}.json")
    with open(output_file, "w", encoding="utf-8") as json_file:
        json.dump(rooms, json_file, ensure_ascii=False, indent=4)

    print(f"JSON file {output_file} created successfully.")

def process_file_pair(svg_file, html_file):
    """Process a pair of SVG and HTML files through the pipeline"""

    base_name = os.path.splitext(svg_file)[0]
    svg_file_path = os.path.join("svg_files", svg_file)
    html_file_path = os.path.join("html_files", html_file)
    os.makedirs("output_files", exist_ok=True)
    
    try:
        geojson_data = process_svg_to_geojson(svg_file_path)

        geojson_data = process_html_room_types(html_file_path, geojson_data)
        
        process_geojson_to_json(geojson_data, base_name)

        print(f"Successfully processed {base_name}")

    except Exception as e:
        print(f"Error processing {base_name}: {e}")
        return

def main():
    """Main pipeline function that processes all SVG and HTML file pairs"""

    svg_files = []
    
    os.makedirs("svg_files", exist_ok=True)
    os.makedirs("html_files", exist_ok=True)
    
    svg_files = [f for f in os.listdir("svg_files") if f.endswith(".svg")]
    html_files = [f for f in os.listdir("html_files") if f.endswith(".html")]

    print(f"Found {len(svg_files)} SVG files and {len(html_files)} HTML files")

    # For each SVG file find a matching HTML file
    for svg_file in svg_files:
        base_name = os.path.splitext(svg_file)[0]
        html_file = f"{base_name}.html"

        if html_file in html_files:
            process_file_pair(svg_file, html_file)
        else:
            print(f"No matching HTML file found for {svg_file}")

    print(f"Pipeline completed.")

if __name__ == "__main__":
    main()