# this script is used to convert the svg file to a geojson file.
# It uses svg_to_geojson.py to convert the svg file to a geojson file.
# then it uses reverts the y coordinate to make the polygon face up.
# then it uses simplify_geojson.py to simplify the geojson file.
# then it uses remove_duplicate_polygon.py to remove the duplicate polygon.

from bs4 import BeautifulSoup
from svgpathtools import parse_path
import geojson
from shapely.geometry import shape, mapping
import xml.etree.ElementTree as ET
import json
from shapely.geometry import Point, Polygon
import geojson
from shapely.ops import nearest_points

file_name = "Ansys-1-map.svg"


def svg_path_to_coords(svg_d, num_points=100):
    path = parse_path(svg_d)
    coords = []
    for seg in path:
        # Sample points along each segment
        for i in range(num_points + 1):
            pt = seg.point(i / num_points)
            coords.append((pt.real, pt.imag))
    return coords


# Load SVG file
with open(file_name, "r") as f:
    soup = BeautifulSoup(f, "xml")

# Extract all <path> elements
paths = soup.find_all("path")

features = []

for i, path in enumerate(paths):
    d = path.get("d")
    if not d:
        continue
    coords = svg_path_to_coords(d)

    # Close the polygon if not already closed
    if coords[0] != coords[-1] and ((coords[0][0] - coords[-1][0])**2 + (coords[0][1] - coords[-1][1])**2)**0.5 > 1:
        # coords.append(coords[0])
        continue
    # print(i)
    polygon = geojson.Polygon([coords])
    feature = geojson.Feature(geometry=polygon, properties={"id": i})
    features.append(feature)


# Wrap as a FeatureCollection
gj = geojson.FeatureCollection(features)

print("convert to .geojson")

# Revert the GeoJSON

# Compute the minimum FLIPPED Y over all features
# min_flipped = float("inf")
# for feat in gj["features"]:
#     # assume Polygon with one outer ring:
#     ring = feat["geometry"]["coordinates"][0]
#     for x, y in ring:
#         flipped = -y
#         if flipped < min_flipped:
#             min_flipped = flipped

# Rewrite every coordinate: flip and then subtract min_flipped
for feat in gj["features"]:
    ring = feat["geometry"]["coordinates"][0]
    new_ring = []
    for x, y in ring:
        y_flipped = -y
        new_ring.append((x, y_flipped))
    feat["geometry"]["coordinates"][0] = new_ring

print("revert the .geojson")
# Simplify the GeoJSON


def is_colinear(p1, p2, p3, tol=1e-6):
    """
    Return True if p1, p2, p3 are (approximately) colinear.
    Uses the cross-product test with a small tolerance.
    """
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    return abs((x2 - x1) * (y3 - y1) - (y2 - y1) * (x3 - x1)) < tol


def simplify_ring(ring):
    """
    Remove any intermediate points in straight segments.
    Properly handles closed rings (first == last).
    """
    # 1) Detect & strip the closing duplicate
    closed = ring[0] == ring[-1]
    coords = ring[:-1] if closed else ring[:]

    if len(coords) <= 2:
        # Nothing to simplify
        return ring

    simplified = [coords[0]]
    for i in range(1, len(coords) - 1):
        p1 = simplified[-1]
        p2 = coords[i]
        p3 = coords[i + 1]

        # Drop p2 if it lies on the line p1→p3
        if not is_colinear(p1, p2, p3):
            simplified.append(p2)

    # Always keep the last “real” point
    simplified.append(coords[-1])

    # Re-close if it was closed
    if closed:
        simplified.append(simplified[0])

    return simplified


for feature in gj["features"]:
    ring = feature["geometry"]["coordinates"][0]
    feature["geometry"]["coordinates"][0] = simplify_ring(ring)

print("remove colinear points")


def normalize_polygon(polygon):
    # Sort the coordinates to ensure consistent order
    return tuple(sorted(map(tuple, polygon)))


def enforce_winding_order(polygon):
    # Use shapely to ensure the polygon has the correct winding order
    shapely_polygon = shape({"type": "Polygon", "coordinates": [polygon]})
    return mapping(shapely_polygon)["coordinates"][0]


def remove_duplicate_polygons(geojson_data):
    feature_collection = {"type": "FeatureCollection", "features": []}
    unique_polygons_id = dict()
    unique_polygons = []

    for feature in geojson_data["features"]:
        if feature["geometry"]["type"] == "Polygon":
            polygon = feature["geometry"]["coordinates"][0]
            # Enforce winding order
            polygon = enforce_winding_order(polygon)
            # Round coordinates to 6 decimal places and normalize
            rounded_polygon = [(round(lon, 6), round(lat, 6)) for lon, lat in polygon]
            polygon_tuple = normalize_polygon(rounded_polygon)

            unique_polygons_id[polygon_tuple] = feature["properties"]["id"]

    unique_polygons_id = list(map(lambda x: x[1], unique_polygons_id.items()))
    cnt = 0
    for feature in geojson_data["features"]:
        if feature["properties"]["id"] in unique_polygons_id:
            ans = feature.copy()
            ans["properties"]["id"] = cnt
            unique_polygons.append(ans)
            cnt += 1
    print(f"there are {len(unique_polygons)} unique polygons")
    feature_collection["features"].extend(unique_polygons)
    return feature_collection


geojson_data_no_duplicates = remove_duplicate_polygons(gj)
# 4) Save out the corrected GeoJSON
# with open(file_name.replace(".svg", "_simplified.geojson"), "w") as f:
#     geojson.dump(geojson_data_no_duplicates, f)

print("remove duplicate polygons")


class Room:
    def __init__(self, name, coordinates):
        self.name = name
        self.coordinates = coordinates


class Poly:
    def __init__(self, id, coordinates):
        self.id = id
        self.coordinates = coordinates


def parse_svg(svg_file):
    tree = ET.parse(svg_file)
    root = tree.getroot()
    namespaces = {"svg": "http://www.w3.org/2000/svg"}

    room_tags = []
    for text in root.findall(".//svg:text", namespaces):
        # Extract the room name from the text content
        room_name = text.text.strip()
        # Extract the coordinates from the attributes
        x = float(text.get("x"))
        y = -float(text.get("y"))
        room = Room(room_name, (x, y))
        room_tags.append(room)

    return room_tags


def parse_geojson(geojson_file):
    # with open(geojson_file) as f:
    #     data = json.load(f)
    data = geojson_file
    polygons = []
    for feature in data["features"]:
        polygon = feature["geometry"]["coordinates"][0]
        polygon_id = feature["properties"]["id"]
        polygon = Poly(polygon_id, polygon)
        polygons.append(polygon)

    return polygons


target_polygon = set([152, 38, 311])


def match_rooms_to_polygons(room_tags, polygons):
    matches = []
    for room in room_tags:
        point = Point(room.coordinates)
        for i in range(len(polygons)):
            polygon_coords = polygons[i].coordinates
            p = Polygon(polygon_coords)
            if p.contains(point):
                matches.append({"polygon": polygons[i], "room": room})
                break
    return matches


# Example usage
room_tags = parse_svg(file_name)
room_tags.sort(key=lambda room: room.name)
polygons = parse_geojson(geojson_data_no_duplicates)
assert len(room_tags) == len(polygons)


matches = match_rooms_to_polygons(room_tags, polygons)

match_room = set()
# print(target_polygon)
for match in matches:
    match_room.add(match["room"])
duplicated_polygon = set()
match_polygon = set()
for match in matches:
    cur_p = match["polygon"]
    if cur_p in match_polygon:
        # print(f"polygon {cur_p.id} is matched to multiple rooms")
        duplicated_polygon.add(cur_p)
    match_polygon.add(cur_p)
# print(f"match room {len(match_room)}")
# print(f"match polygon{len(match_polygon)}")

duplicated_room = set()
id_to_room = dict()
name_to_id = dict()
for match in matches:
    cur_p = match["polygon"]
    if cur_p in duplicated_polygon:
        duplicated_room.add(match["room"])
        name_to_id[match["room"].name] = cur_p
        if cur_p.id in id_to_room:
            id_to_room[cur_p.id].append(match["room"])
        else:
            id_to_room[cur_p.id] = [match["room"]]
n_duplicated_polygon = len(duplicated_polygon)
n_duplicated_room = len(duplicated_room)
# print(f"Number of duplicated polygons: {len(duplicated_polygon)}")
# print(f"Number of duplicated rooms: {len(duplicated_room)}")

unmatched_room = [room for room in room_tags if room not in match_room]

# # Find indices of polygons that are not matched
unmatched_polygons = [polygon for polygon in polygons if polygon not in match_polygon]
n_unmatched_room = len(unmatched_room)
n_unmatched_polygons = len(unmatched_polygons)
# print(f"Number of unmatched rooms: {len(unmatched_room)}")
# print(f"Number of unmatched polygons: {len(unmatched_polygons)}")
# print(len(matches))

assert (
    n_duplicated_room + n_unmatched_room == n_duplicated_polygon + n_unmatched_polygons
)

# TODO: get rooms matches with polygons, for all rooms and polygon. Sort based on distance.
# If an unmatched polygon is matched with a room, remove room from duplicated if necessary. Match all eventually.

# Function to calculate distance between a point and a polygon


def calculate_distance(point, polygon):
    point_geom = Point(point)
    polygon_geom = Polygon(polygon)
    nearest_geom = nearest_points(point_geom, polygon_geom)[1]
    return point_geom.distance(nearest_geom)


for room in unmatched_room:
    room_point = Point(room.coordinates)
    distances = []
    for polygon in unmatched_polygons:
        polygon_coords = polygon.coordinates
        distance = calculate_distance(room_point, polygon_coords)
        distances.append((distance, polygon))
    # Sort by distance
    distances.sort(key=lambda x: x[0])
    # Match the closest polygon
    closest_polygon = distances[0][1]
    matches.append({"room": room, "polygon": closest_polygon})
    # Update matched sets
    # Remove matched room and polygon from unmatched lists
    unmatched_polygons.remove(closest_polygon)

for polygon in unmatched_polygons:
    # print(len(duplicated_room))
    polygon_coords = polygon.coordinates
    distances = []
    for room in duplicated_room:
        room_point = Point(room.coordinates)
        distance = calculate_distance(room_point, polygon_coords)
        distances.append((distance, room))
        # print(room.name)
    distances.sort(key=lambda x: x[0])
    # print(distances)
    closest_room = distances[0][1]
    # print(f"closest room: {closest_room.name}")
    matches.append({"room": closest_room, "polygon": polygon})
    duplicated_room.remove(closest_room)
    pid = name_to_id[closest_room.name].id
    matches.remove({"room": closest_room, "polygon": name_to_id[closest_room.name]})
    id_to_room[pid].remove(closest_room)
    if len(id_to_room[pid]) == 1:
        duplicated_room.remove(id_to_room[pid][0])

# for match in matches:
#     print(f"room {match['room'].name} is matched with polygon {match['polygon'].id}")
# print(len(room_tags))
# print(len(polygons))
assert len(room_tags) == len(matches)


# Create a list to hold all the features
features = []

# Iterate over the matches to create features
for match in matches:
    polygon = match["polygon"]
    room = match["room"]

    # Create a GeoJSON feature for the polygon
    polygon_feature = geojson.Feature(
        geometry=geojson.Polygon([polygon.coordinates]),
        properties={"id": polygon.id, "room_name": room.name, "labelPosition": room.coordinates},
    )

    # Add the feature to the list
    features.append(polygon_feature)

# Create a FeatureCollection from the features
feature_collection = geojson.FeatureCollection(features)

# Write the FeatureCollection to a GeoJSON file
with open(f"{file_name.replace('.svg', '')}.geojson", "w") as f:
    geojson.dump(feature_collection, f, indent=2)

print("GeoJSON file 'polygons_with_rooms.geojson' created successfully.")