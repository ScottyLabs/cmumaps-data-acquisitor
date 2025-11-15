import os
import json
import re
from bs4 import BeautifulSoup
from pathlib import Path

def extract_floor_info_from_html(html_content):
    """
    Extract floor information from HTML content.
    Returns a dictionary mapping floor names to floor IDs.
    """
    floor_info = {}

    # Parse HTML with BeautifulSoup
    soup = BeautifulSoup(html_content, "html.parser")

    # Find all <a> tags with class="rtIn" (these contain floor information)
    floor_links = soup.find_all("a", class_="rtIn")

    for link in floor_links:
        # Get the title attribute (floor name) and id attribute (floor ID)
        title = link.get("title")
        floor_id = link.get("id")

        if title and floor_id:
            floor_info[title] = floor_id

    return floor_info


def process_building_codes_directory(path: str = None):
    """
    Process all HTML files in the building_codes directory and create a JSON file
    with building and floor information.
    """
    output_data = []
    if path is None:
        building_codes_dir = Path("building_codes")

        # Check if directory exists
        if not building_codes_dir.exists():
            print(f"Error: Directory '{building_codes_dir}' does not exist.")
            return

        # Get all HTML files in the directory
        html_files = list(building_codes_dir.glob("*.html"))

        if not html_files:
            print(f"No HTML files found in '{building_codes_dir}' directory.")
            return
    else:

        html_files = [Path(path)]

    print(f"Found {len(html_files)} HTML files to process:")

    for html_file in html_files:
        print(f"Processing: {html_file.name}")

        try:
            # Read the HTML file
            with open(html_file, "r", encoding="utf-8") as f:
                html_content = f.read()

            # Extract floor information
            floor_info = extract_floor_info_from_html(html_content)

            # Create building entry
            building_entry = {
                "building": html_file.stem,  # filename without extension
                "floorid": floor_info,
            }

            output_data.append(building_entry)
            print(f"  - Extracted {len(floor_info)} floors: {list(floor_info.keys())}")

        except Exception as e:
            print(f"  - Error processing {html_file.name}: {str(e)}")

    # Write to JSON file
    if not path:
        output_file = "all_building_codes.json"
    else:
        output_file = f"{(path.split('/')[-1]).split('.')[0]}.json"
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(
            f"\nSuccessfully created '{output_file}' with {len(output_data)} buildings."
        )
        print(
            f"Total floors across all buildings: {sum(len(building['floorid']) for building in output_data)}"
        )

    except Exception as e:
        print(f"Error writing JSON file: {str(e)}")


def main():
    """
    Main function to run the building codes processing,
    assuming all the building html files are in a directory.
    """
    print("Starting building codes processing...")
    process_building_codes_directory()
    print("Processing complete!")


def run_building(filepath):
    """
    Function to run the building codes processing.
    """
    print("Starting building codes processing...")
    process_building_codes_directory(filepath)
    print("Processing complete!")


if __name__ == "__main__":
    # For example, your file might be downloaded in your Downloads folder as "ShowDrawingView.html".
    # Please rename the file to the name of the building.
    filepath = "/Users/username/Downloads/ansys.html"
    run_building(filepath)
