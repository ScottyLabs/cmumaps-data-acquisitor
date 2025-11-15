import xml.etree.ElementTree as ET
import json
from geopy import distance


# change to the location of the export.osm file
tree = ET.parse("../data/export.osm")
root = tree.getroot()

# holds all of the nodes
# will be converted to a JSON at the end
nodes = {}

# all of the tags of ways that should not be used
excluded_tags = ["building", "leisure"]

for child in root:
    # create a json node for each node in the export
    if child.tag == 'node':
        node_attributes = child.attrib
        current_node = {
            "neighbors": {}, "coordinate": {"latitude": node_attributes['lat'], "longitude": node_attributes['lon']}, "id": node_attributes['id'], "tags": {}, "way_tags": {}}
        # adds all nodes, including ones that define bounds of buildings/parks
        # these should be removed
        nodes[node_attributes['id']] = current_node
        for tag in child:
            current_node["tags"][tag.attrib['k']] = tag.attrib['v']

    # all nodes are earlier in the file than the ways
    # so treating ways like this is fine
    elif child.tag == 'way':
        way = child
        way_tags = way.findall("tag")
        exclude = False
        for tag in way_tags:
            if (tag.attrib["k"] in excluded_tags):
                exclude = True
        way_nodes = way.findall("nd")
        for i in range(0, len(way_nodes)):
            # nodes for buildings are not guaranteed to not be in any ways for paths
            # so you can't just remove any nodes that are in buildings

            current_node = nodes.get(way_nodes[i].attrib["ref"], False)
            if current_node:
                for tag in way_tags:
                    current_node["tags"][tag.attrib['k']] = tag.attrib['v']
                if not exclude:
                    if i > 0:
                        compare_node = nodes.get(
                            way_nodes[i-1].attrib["ref"], False)
                        if compare_node:
                            dist = distance.distance(
                                (compare_node["coordinate"]["latitude"], compare_node["coordinate"]["longitude"]), (current_node["coordinate"]["latitude"], current_node["coordinate"]["longitude"]))
                            # distance is stored in meters
                            current_node["neighbors"][compare_node["id"]] = {
                                "dist": dist.m}
                    if i < len(way_nodes)-1:
                        compare_node = nodes.get(
                            way_nodes[i+1].attrib["ref"], False)
                        if compare_node:
                            dist = distance.distance(
                                (compare_node["coordinate"]["latitude"], compare_node["coordinate"]["longitude"]), (current_node["coordinate"]["latitude"], current_node["coordinate"]["longitude"]))
                            # distance is stored in meters
                            current_node["neighbors"][compare_node["id"]] = {
                                "dist": dist.m}
                elif exclude and current_node["tags"].get("entrance", False):
                    for tag in way_tags:
                        if tag.attrib['k'] == "name":
                            current_node["entrance"] = tag.attrib['v']
                elif exclude:
                    # safe to pop anything that isn't an entrance but is a building
                    nodes.pop(way_nodes[i].attrib["ref"])


with open("osm-data.json", 'w') as file:
    json.dump(nodes, file, indent=4)
