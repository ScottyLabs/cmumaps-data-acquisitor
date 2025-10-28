import json


def transform_json_to_geojson(input_file, output_file):
    """
    Transform ansys.json format to GeoJSON format.

    Args:
        input_file: Path to the input ansys.json file
        output_file: Path to the output GeoJSON file
    """
    # Read the input file
    with open(input_file, "r") as f:
        ansys_data = json.load(f)

    # Initialize GeoJSON structure
    geojson = {"type": "FeatureCollection", "features": []}

    # Transform each room to a GeoJSON feature
    for room_number, room_data in ansys_data.items():
        # Create a polygon feature for the room boundary
        if room_data.get("points") and len(room_data["points"]) > 0:
            # Extract coordinates and convert to GeoJSON format
            # GeoJSON uses [longitude, latitude] order (opposite of the source)
            coordinates = []
            for polygon in room_data["points"]:
                polygon_coords = []
                for point in polygon:
                    # Convert from {latitude, longitude} to [longitude, latitude]
                    polygon_coords.append([point["longitude"], point["latitude"]])
                # Ensure the polygon is closed (first point == last point)
                if polygon_coords and polygon_coords[0] != polygon_coords[-1]:
                    polygon_coords.append(polygon_coords[0])
                coordinates.append(polygon_coords)

            # Create the feature with properties
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon" if len(coordinates) == 1 else "MultiPolygon",
                    "coordinates": (
                        coordinates if len(coordinates) == 1 else [coordinates]
                    ),
                },
                "properties": {
                    "room_number": room_number,
                    "type": room_data.get("type"),
                    "buildingCode": room_data.get("floor", {}).get("buildingCode"),
                    "level": room_data.get("floor", {}).get("level"),
                    "labelLatitude": room_data.get("labelPosition", {}).get("latitude"),
                    "labelLongitude": room_data.get("labelPosition", {}).get(
                        "longitude"
                    ),
                },
            }

            # Add alias if it exists
            if "alias" in room_data:
                feature["properties"]["alias"] = room_data["alias"]

            geojson["features"].append(feature)

    # Write the output file
    with open(output_file, "w") as f:
        json.dump(geojson, f, indent=2)

    print(f"Successfully transformed {len(geojson['features'])} rooms to GeoJSON")
    print(f"Output saved to: {output_file}")


if __name__ == "__main__":
    transform_ansys_to_geojson("ansys_1.json", "ansys_1.geojson")
