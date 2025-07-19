import geojson
import json
import uuid
import os

def main():
    file_name = "Ansys-1-map_updated.geojson"
    with open(os.path.join("geojson_files", file_name), "r", encoding="utf-8") as f:
        polygons = geojson.load(f)

    rooms = dict()

    for feature in polygons["features"]:
        elements = dict()
        elements["name"] = feature["properties"]["room_name"]
        elements["labelPosition"] = dict()
        elements["labelPosition"]["longitude"] = feature["properties"]["labelPosition"][0]
        elements["labelPosition"]["latitude"] = feature["properties"]["labelPosition"][1]
        elements["type"] = feature["properties"]["room_type"]
        elements["id"] = str(uuid.uuid4())
        elements["coordinates"] = []
        elements['floor'] = dict()
        elements['floor']['level'] = file_name.split('-')[1]
        # print(elements['floor']['level'])

        for polygon in feature["geometry"]["coordinates"][0]:
            poly_cord = []
            p = dict()
            p['longitude'] = polygon[0]
            p['latitude'] = polygon[1]
            poly_cord.append(p)
            elements["coordinates"].append(poly_cord)
        rooms[elements["id"]] = elements
    
    output_file = file_name.replace('_updated.geojson', '.json')
    output_file_name = os.path.join("json_files", output_file)
    with open(output_file_name, "w", encoding="utf-8") as json_file:
        json.dump(rooms, json_file, ensure_ascii=False, indent=4)
    print(f"GeoJSON file {file_name} converted to JSON file {output_file_name} successfully.")

if __name__ == "__main__":
    main()

