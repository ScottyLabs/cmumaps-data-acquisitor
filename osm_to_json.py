# Generalized function to find entrance pairs between OSM and nodes from any floor level

import xml.etree.ElementTree as ET
import json
from geopy import distance
import math
import sys
import argparse


DISTANCE_THRESHOLD_METERS = 10.0  #threshold for the distance, adjust if needed

def load_graph_data(file_path="downloaded_all_graphs.json"):
    """Load the graph data from JSON file"""
    print(f"Loading {file_path}...")
    with open(file_path, 'r') as f:
        return json.load(f)

def extract_floor_nodes(graph_data, floor_level):
    """Extract all nodes from a specific floor level"""
    floor_nodes = {}
    floor_level_str = str(floor_level)
    
    print(f"Extracting floor level {floor_level} nodes from graph data...")
    
    for node_id, node_data in graph_data.items():
        if ('floor' in node_data and 
            'coordinate' in node_data and 
            node_data['floor'].get('level') == floor_level_str):
            
            floor_nodes[node_id] = node_data
    
    print(f"Found {len(floor_nodes)} nodes on floor level {floor_level}")
    return floor_nodes

def save_floor_nodes(floor_nodes, floor_level, output_file=None):
    """Save floor nodes to a JSON file"""
    if output_file is None:
        output_file = f"floor_{floor_level}_nodes.json"
    
    print(f"Saving floor {floor_level} nodes to {output_file}...")
    with open(output_file, 'w') as f:
        json.dump(floor_nodes, f, indent=2)
    
    print(f"Floor {floor_level} nodes saved to '{output_file}'")
    return output_file

def parse_osm_entrances(osm_file_path="export (1).osm"):
    """Parse OSM file and extract entrance nodes"""
    print(f"Parsing OSM file: {osm_file_path}...")
    tree = ET.parse(osm_file_path)
    root = tree.getroot()
    
    osm_entrances = []
    print("Extracting entrance nodes from OSM...")
    
    for child in root:
        if child.tag == 'node':
            # check if this node has entrance tags
            entrance_tags = child.findall("tag[@k='entrance']")
            if entrance_tags:
                node_attrib = child.attrib
                entrance_type = entrance_tags[0].attrib.get('v', 'yes')
                
                # try to find floor level information
                floor_level = None
                building_code = None
                
                # look for level tags
                level_tags = child.findall("tag[@k='level']")
                if level_tags:
                    try:
                        floor_level = int(level_tags[0].attrib.get('v', '0'))
                    except ValueError:
                        floor_level = 0
                
                # look for building information
                building_tags = child.findall("tag[@k='building']")
                if building_tags:
                    building_code = building_tags[0].attrib.get('v', 'unknown')
                
                osm_entrances.append({
                    'id': node_attrib['id'],
                    'lat': float(node_attrib['lat']),
                    'lon': float(node_attrib['lon']),
                    'entrance_type': entrance_type,
                    'floor_level': floor_level,
                    'building_code': building_code
                })
    
    print(f"Found {len(osm_entrances)} entrance nodes in OSM file")
    return osm_entrances

def calculate_distance(lat1, lon1, lat2, lon2):
    return distance.distance((lat1, lon1), (lat2, lon2)).meters

def find_entrance_pairs(osm_entrances, floor_nodes, floor_level, distance_threshold=DISTANCE_THRESHOLD_METERS):
    matches = []
    
    print(f"Finding best floor {floor_level} node match for each OSM entrance...")
    
    for osm_entrance in osm_entrances:
        # keep track distances for
        same_floor_matches = []
        other_floor_matches = []
        
        for node_id, floor_node in floor_nodes.items():
            # calculate distance
            dist = calculate_distance(
                osm_entrance['lat'], osm_entrance['lon'],
                floor_node['coordinate']['latitude'], 
                floor_node['coordinate']['longitude']
            )
            
            # Only consider if within distance threshold
            if dist <= distance_threshold:
 
                exact_floor_match = False
                if osm_entrance['floor_level'] is not None:
                    if osm_entrance['floor_level'] == floor_level:
                        exact_floor_match = True
                else:
                    # assume ground level (floor 1) since many dont have values
                    if floor_level == 1:
                        exact_floor_match = True
                
                match_data = {
                    'floor_node': {
                        'id': node_id,
                        'lat': floor_node['coordinate']['latitude'],
                        'lon': floor_node['coordinate']['longitude'],
                        'floor_level': int(floor_node['floor']['level']),
                        'building_code': floor_node['floor']['buildingCode'],
                        'room_id': floor_node.get('roomId', ''),
                        'pos': floor_node.get('pos', {}),
                        'neighbors': floor_node.get('neighbors', {})
                    },
                    'distance': dist
                }
                
                if exact_floor_match:
                    same_floor_matches.append(match_data)
                else:
                    other_floor_matches.append(match_data)
        
        same_floor_matches.sort(key=lambda x: x['distance']) #sorting for finding the best one
        other_floor_matches.sort(key=lambda x: x['distance']) #sorting for finding the best one
        
        best_match = None
        if same_floor_matches:
            best_match = same_floor_matches[0]  # closest same floor match
        elif other_floor_matches:
            best_match = other_floor_matches[0]  # closest other floor match
        
        # Add the best match if found
        if best_match:
            matches.append({
                'osm_entrance': osm_entrance,
                'floor_node': best_match['floor_node'],
                'distance_meters': best_match['distance']
            })
    
    print(f"Found {len(matches)} pairs (1 best match per OSM entrance)")
    return matches

def save_results(entrance_pairs, floor_level, floor_nodes, osm_entrances, output_file=None):
    """Save results to JSON file"""
    if output_file is None:
        output_file = f"entrance_pairs_floor_{floor_level}.json"
    
    output_data = {
        'floor_level': floor_level,
        'total_pairs': len(entrance_pairs),
        'distance_threshold_meters': DISTANCE_THRESHOLD_METERS,
        'floor_nodes_count': len(floor_nodes),
        'osm_entrances_count': len(osm_entrances),
        'pairs': entrance_pairs
    }

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"\nResults saved to '{output_file}'")
    return output_file

graph_data = load_graph_data("downloaded_all_graphs.json")

#Change it to a floor you need
floor_2_nodes = extract_floor_nodes(graph_data, 2)

#parsing osm
osm_entrances = parse_osm_entrances("export (1).osm")

#finding pairs
pairs = find_entrance_pairs(osm_entrances, floor_2_nodes, 2)

# export results to JSON file
save_results(pairs, 2, floor_2_nodes, osm_entrances, "my_floor_2_results.json")

### Wasn't sure if this code is completely correct since some of the floor levels are completely wrong, since  
#   some of these buildings are wrong too (I saw a coord that was actually CUC when put in GMaps which said DH)
#   This is why I added the code to check for the best floor match or other level match since some did not 
#  coincide at all. I think possible fix could be just not passing in floor as argument since I feel that 
# adds a level of complexity that might just make our pairing less accurate. It might be easier to just get raw 
# pairings without floor level as argument if we are dealing with faulty ESIM data.###