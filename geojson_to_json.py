import geojson
import json
import uuid

with open("polygons_with_rooms_updated.geojson", "r", encoding="utf-8") as f:
    polygons = geojson.load(f)

rooms = dict()

for feature in polygons["features"]:
    elements = dict()
    elements["name"] = feature["properties"]["room_name"]
    elements["labelPosition"] = feature["properties"]["labelPosition"]
    elements["type"] = feature["properties"]["room_type"]
    elements["polygon"] = feature["geometry"]
    rooms[str(uuid.uuid4())] = elements

    with open("rooms.json", "w", encoding="utf-8") as json_file:
        json.dump(rooms, json_file, ensure_ascii=False, indent=4)



