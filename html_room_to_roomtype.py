from bs4 import BeautifulSoup
import geojson


# Load your HTML file
with open("output.html", "r", encoding="utf-8") as f:
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

# Example: print mapping
for k, v in room_map.items():
    print(f"{k} -> {v}")


# Load the GeoJSON file containing polygons with rooms
with open("polygons_with_rooms.geojson", "r", encoding="utf-8") as f:
    polygons = geojson.load(f)

# Iterate over each feature in the GeoJSON
for feature in polygons["features"]:
    # Get the room number from the feature's properties
    room_name = feature["properties"].get("room_name")

    # Find the room type using the room_map
    room_type = room_map[room_name]

    # Add the room type to the feature's properties
    feature["properties"]["room_type"] = room_type

# Save the updated GeoJSON back to a file
with open("polygons_with_rooms_updated.geojson", "w", encoding="utf-8") as f:
    geojson.dump(polygons, f, ensure_ascii=False, indent=2)



