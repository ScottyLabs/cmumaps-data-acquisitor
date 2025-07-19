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
from shapely.geometry import Point, Polygon, MultiPolygon
from shapely.ops import nearest_points, unary_union
import os

class Room:
    def __init__(self, name, coordinates):
        self.name = name
        self.coordinates = coordinates

class Poly:
    def __init__(self, id, coordinates):
        self.id = id
        self.coordinates = coordinates

def svg_path_to_coords(svg_d, num_points=100):
    path = parse_path(svg_d)
    coords = []
    for seg in path:
        # Sample points along each segment
        for i in range(num_points + 1):
            pt = seg.point(i / num_points)
            coords.append((pt.real, pt.imag))
    return coords

def load_svg(file_name):
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
    for feat in gj["features"]:
        ring = feat["geometry"]["coordinates"][0]
        new_ring = []
        for x, y in ring:
            y_flipped = -y
            new_ring.append((x, y_flipped))
        feat["geometry"]["coordinates"][0] = new_ring
    print("revert the .geojson")

    return gj

def remove_duplicate_points(ring):
    new_ring = []
    for i in range(len(ring) - 1):
        if ring[i] != ring[i + 1]:
            new_ring.append(ring[i])
    new_ring.append(ring[-1])
    return new_ring

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
    ring = remove_duplicate_points(ring)
    if len(ring) == 1:
        return ring
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

def simplify_geojson(gj):
    keep_features = []
    for feature in gj["features"]:
        ring = feature["geometry"]["coordinates"][0]
        feature["geometry"]["coordinates"][0] = simplify_ring(ring)
        if len(feature["geometry"]["coordinates"][0]) > 2:
            keep_features.append(feature)
    gj["features"] = keep_features
    print("remove colinear points")
    return gj

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
    print("remove duplicate polygons")
    return feature_collection

def remove_covered_polygons(geojson_data):
    """
    Remove polygons that are completely covered by other polygons.
    Returns a new FeatureCollection with covered polygons removed.
    """
    features = geojson_data["features"]
    features_to_keep = []
    
    for i, feature1 in enumerate(features):
        if feature1["geometry"]["type"] != "Polygon":
            features_to_keep.append(feature1)
            continue
            
        polygon1 = shape(feature1["geometry"])
        is_covered = False
        
        for j, feature2 in enumerate(features):
            if i == j or feature2["geometry"]["type"] != "Polygon":
                continue
                
            polygon2 = shape(feature2["geometry"])
            
            # Check if polygon1 is completely covered by polygon2
            if polygon2.contains(polygon1):
                is_covered = True
                break
        
        if not is_covered:
            features_to_keep.append(feature1)
    
    result = {
        "type": "FeatureCollection",
        "features": features_to_keep
    }
    
    print(f"Removed {len(features) - len(features_to_keep)} covered polygons")
    return result

def combine_overlapping_polygons(geojson_data):
    """
    Combine overlapping polygons into a single polygon that follows the outermost boundary.
    Only merges polygons that actually overlap (share area), not just touch.
    """
    features = geojson_data["features"]
    if len(features) <= 1:
        return geojson_data
    
    # Convert to Shapely polygons for easier manipulation
    shapely_polygons = []
    for feature in features:
        if feature["geometry"]["type"] == "Polygon":
            polygon = shape(feature["geometry"])
            shapely_polygons.append(polygon)
    
    if len(shapely_polygons) <= 1:
        return geojson_data
    
    # Find overlapping polygon groups
    overlapping_groups = []
    used_indices = set()
    
    for i in range(len(shapely_polygons)):
        if i in used_indices:
            continue
            
        # Start a new group with polygon i
        current_group = [i]
        used_indices.add(i)
        
        # Check for overlaps with other polygons
        changed = True
        while changed:
            changed = False
            for j in range(len(shapely_polygons)):
                if j in used_indices:
                    continue
                    
                # Check if polygon j overlaps with any polygon in current group
                for group_idx in current_group:
                    if shapely_polygons[group_idx].intersects(shapely_polygons[j]):
                        # Check if they actually overlap (share area), not just touch
                        intersection = shapely_polygons[group_idx].intersection(shapely_polygons[j])
                        if intersection.area > 0:  # They share area
                            current_group.append(j)
                            used_indices.add(j)
                            changed = True
                            break
                if changed:
                    break
        
        if len(current_group) > 1:
            overlapping_groups.append(current_group)
        else:
            # Single polygon, no overlaps
            overlapping_groups.append([i])
    
    # Merge overlapping groups and keep non-overlapping polygons as-is
    result_features = []
    feature_id = 0
    
    for group in overlapping_groups:
        if len(group) == 1:
            # Single polygon, no overlaps
            original_feature = features[group[0]]
            new_feature = geojson.Feature(
                geometry=original_feature["geometry"],
                properties={"id": feature_id, "merged": False}
            )
            result_features.append(new_feature)
            feature_id += 1
        else:
            # Merge overlapping polygons
            polygons_to_merge = [shapely_polygons[i] for i in group]
            merged_polygon = unary_union(polygons_to_merge)
            
            if merged_polygon.geom_type == "Polygon":
                new_feature = geojson.Feature(
                    geometry=mapping(merged_polygon),
                    properties={"id": feature_id, "merged": True, "merged_from": group}
                )
                result_features.append(new_feature)
                feature_id += 1
            elif isinstance(merged_polygon, MultiPolygon):
                # Handle case where union creates multiple polygons
                for i, polygon in enumerate(merged_polygon.geoms):
                    new_feature = geojson.Feature(
                        geometry=mapping(polygon),
                        properties={"id": feature_id, "merged": True, "merged_from": group}
                    )
                    result_features.append(new_feature)
                    feature_id += 1
    
    result = geojson.FeatureCollection(result_features)
    
    original_count = len(features)
    result_count = len(result_features)
    print(f"Combined overlapping polygons: {original_count} -> {result_count} polygons")
    
    return result

def get_room_tags(svg_file):
    tree = ET.parse(svg_file)
    root = tree.getroot()
    namespaces = {"svg": "http://www.w3.org/2000/svg"}
    seen = set()
    room_tags = []
    for text in root.findall(".//svg:text", namespaces):
        # Extract the room name from the text content
        room_name = text.text.strip() if text.text else ""
        if not room_name:
            continue
        # Extract the coordinates from the attributes
        x_attr = text.get("x")
        y_attr = text.get("y")
        if x_attr is None or y_attr is None:
            continue
        x = float(x_attr)
        y = -float(y_attr)
        if room_name not in seen:
            room = Room(room_name, (x, y))
            room_tags.append(room)
            seen.add(room_name)
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

def calculate_distance(point, polygon):
    point_geom = Point(point)
    polygon_geom = Polygon(polygon)
    nearest_geom = nearest_points(point_geom, polygon_geom)[1]
    return point_geom.distance(nearest_geom)

def get_match_polygons(file_name, geojson_file, strict = True):
    room_tags = get_room_tags(file_name)
    room_tags.sort(key=lambda room: room.name)
    i = 0
    for room in room_tags:
        print(f"{i} {room.name}")
        i += 1

    polygons = parse_geojson(geojson_file)
    print(len(room_tags))
    print(len(polygons))
    if strict:
        assert len(room_tags) == len(polygons)
    else:
        assert len(room_tags) <= len(polygons)


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
    if strict:
        assert (
            n_duplicated_room + n_unmatched_room == n_duplicated_polygon + n_unmatched_polygons
        )




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
    no_tag_polygon = []
    for polygon in unmatched_polygons:
        # print(len(duplicated_room))
        polygon_coords = polygon.coordinates
        distances = []
        for room in duplicated_room:
            room_point = Point(room.coordinates)
            distance = calculate_distance(room_point, polygon_coords)
            distances.append((distance, room))
        if len(distances) == 0:
            no_tag_polygon.append(polygon)
            continue
        distances.sort(key=lambda x: x[0])
        closest_room = distances[0][1]
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
    for polygon in no_tag_polygon:
        polygon_feature = geojson.Feature(
            geometry=geojson.Polygon([polygon.coordinates]),
            properties={"id": polygon.id, "room_name": "no_tag", "labelPosition": polygon.coordinates},
        )
        features.append(polygon_feature)

    # Create a FeatureCollection from the features
    feature_collection = geojson.FeatureCollection(features)
    return feature_collection

def main():
    file_name = "svg_files/Ansys-a-map.svg"
    gj = load_svg(file_name)
    gj = simplify_geojson(gj)
    gj = remove_duplicate_polygons(gj)
    gj = remove_covered_polygons(gj)
    gj = combine_overlapping_polygons(gj)
    with open(f"{file_name.replace('.svg', '')}_no_duplicates.geojson", "w") as f:
        geojson.dump(gj, f, indent=2)
    feature_collection = get_match_polygons(file_name, gj, strict=False)
    # Write the FeatureCollection to a GeoJSON file in geojson_files folder
    base_name = os.path.basename(file_name).replace('.svg', '.geojson')
    output_path = os.path.join('geojson_files', base_name)
    with open(output_path, "w") as f:
        geojson.dump(feature_collection, f, indent=2)

    print(f"GeoJSON file {output_path} created successfully.")

if __name__ == "__main__":
    main()