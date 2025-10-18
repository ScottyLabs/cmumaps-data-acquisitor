# Takes in an OSM file and parses the building info inside of it.
# Creates a new json file with the building data, matching the
# structure used in downloaded_buildings.json.

# Coverage:
# Building ways
# Building relations
# Entrances (both on the outline and inside)
# Floors derived from building:levels and building:levels:underground
# Shapes as closed polygons [{latitude, longitude}, ...]
# Hitbox as closed convex hull of all exterior vertices
# labelPosition as interior visual center

# Notes:
# "defaultFloor" and "code" are sourced from the mapping files.
# All IDs are stored as strings to match the sample JSON.

# How to Run
# Download "downloaded_buildings.json" from S3 bucket
# Import an osm file and change "OSM_FILE" to match

# Created Files
# building_info_map.json - Mapping of abbreviation and default floor level with building name
# parsed_building.json - The data with details about the parsed buildings. 

import xml.etree.ElementTree as ET
import json, math, heapq, os

# Input
OSM_FILE = "export.osm 2"
DOWNLOADED_BUILDINGS_JSON = "downloaded_buildings.json"

# Output
BUILDING_MAPPING_OUTPUT_JSON = "building_info_map.json"
PARSED_DATA_OUTPUT_JSON = "parsed_buildings.json"

# Create mapping from building code to building info from provided JSON files
osm_id_to_info = {}
building_info_map = {}
try:
    # Read the primary source of building data
    with open(DOWNLOADED_BUILDINGS_JSON, 'r') as f:
        downloaded_buildings = json.load(f)

    # Iterate once to create both the file and the internal map
    for code, data in downloaded_buildings.items():
        # Data for building_info_map.json
        building_info_map[code] = {
            "name": data.get("name", ""),
            "code": code,
            "defaultFloor": data.get("defaultFloor", "1")
        }
        
        # Data for the internal osm_id_to_info map used for parsing
        osm_id = data.get("osmId")
        if osm_id:
            osm_id_to_info[osm_id] = {
                "code": code,
                "name": data.get("name", "Unknown"),
                "defaultFloor": data.get("defaultFloor", "1")
            }

    # Write the new building_info_map.json file
    with open(BUILDING_MAPPING_OUTPUT_JSON, 'w') as f:
        json.dump(building_info_map, f, indent=4)
    
    print(f"Successfully created {BUILDING_MAPPING_OUTPUT_JSON} with {len(building_info_map)} buildings.")

except FileNotFoundError as e:
    print(f"Error: Could not find {DOWNLOADED_BUILDINGS_JSON}. {e}. Aborting.")
    exit()
except json.JSONDecodeError as e:
    print(f"Error: Could not parse {DOWNLOADED_BUILDINGS_JSON}. {e}. Aborting.")
    exit()

# Computes what and how many buildings are missing in parsed_buildings from downloaded_buildings
# Note: (1) Posner Center has same OSM ID as Kraus Campo. (2) Scott Hall does not have a OSM ID
def analyze_missing_buildings():
    if not os.path.exists("building_info_map.json") or not os.path.exists("parsed_buildings.json"):
        print("Missing input files (building_info_map.json or parsed_buildings.json).")
        return

    with open("building_info_map.json", "r", encoding="utf-8") as f:
        building_info = json.load(f)

    with open("parsed_buildings.json", "r", encoding="utf-8") as f:
        parsed_buildings = json.load(f)

    parsed_names = set()

    # Support both list or dict structures
    if isinstance(parsed_buildings, dict):
        buildings_iter = parsed_buildings.values()
    elif isinstance(parsed_buildings, list):
        buildings_iter = parsed_buildings
    else:
        print("Unexpected structure in parsed_buildings.json.")
        return

    for b in buildings_iter:
        if isinstance(b, dict):
            name = b.get("name") or b.get("building") or b.get("code")
            if name:
                parsed_names.add(name.strip().lower())

    missing = {}
    for code, info in building_info.items():
        if info["name"].strip().lower() not in parsed_names:
            missing[code] = info

    with open("missing_buildings.json", "w", encoding="utf-8") as f:
        json.dump(missing, f, indent=2, ensure_ascii=False)

    print(f"{len(missing)} buildings missing from parsed_buildings.json")
    if missing:
        print("Missing buildings:")
        for code, info in missing.items():
            print(f" - {info['name']} ({code})")
            
# Geometry helpers
def close_ring(pts):
    """Ensure a polygon ring is closed (first point = last point)."""
    return pts + [pts[0]] if pts and pts[0] != pts[-1] else pts

def polygon_area_and_centroid(ring):
    """Compute signed area and centroid of a closed polygon ring using shoelace formula"""
    n = len(ring)
    if n < 4:
        # fallback: average of points
        xs, ys = zip(*ring) if ring else ([], [])
        return 0, (sum(xs)/len(xs) if xs else 0), (sum(ys)/len(ys) if ys else 0)
    A = Cx = Cy = 0
    for i in range(n-1):
        x0, y0 = ring[i]
        x1, y1 = ring[i+1]
        cross = x0*y1 - x1*y0
        A += cross
        Cx += (x0 + x1) * cross
        Cy += (y0 + y1) * cross
    A *= 0.5
    if A == 0:
        xs, ys = zip(*ring[:-1]) if ring[:-1] else ([], [])
        return 0, (sum(xs)/len(xs) if xs else 0), (sum(ys)/len(ys) if ys else 0)
    return A, Cx/(6*A), Cy/(6*A)

def convex_hull(points):
    """Compute convex hull from a set of points and finds the
    smallest convex polygon containing all points, i.e. the hitbox"""
    def cross(o, a, b): return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
    pts = sorted(set(points))
    if len(pts) <= 1: return close_ring(pts)
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0: lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0: upper.pop()
        upper.append(p)
    return close_ring(lower[:-1] + upper[:-1])

def point_in_ring(pt, ring):
    """Determines whether a point is inside a polygon ring using ray casting"""
    x, y = pt; inside = False
    for i in range(len(ring)-1):
        x1, y1 = ring[i]; x2, y2 = ring[i+1]
        if (y1 > y) != (y2 > y):
            x_int = (x2-x1)*(y-y1)/(y2-y1+1e-16) + x1
            if x_int > x: inside = not inside
    return inside

def point_in_multipolygon(pt, rings):
    """Check if a point is inside any exterior ring."""
    return any(point_in_ring(pt, r) for r in rings)

# Polylabel (Finds the visual center of a polygon)
def point_segment_distance(x,y,x1,y1,x2,y2):
    """Distance from (x,y) to segment (x1,y1)-(x2,y2)."""
    dx, dy = x2-x1, y2-y1
    if dx == dy == 0: return math.hypot(x-x1, y-y1)
    t = max(0, min(1, ((x-x1)*dx+(y-y1)*dy)/(dx*dx+dy*dy)))
    px, py = x1+t*dx, y1+t*dy
    return math.hypot(x-px, y-py)

def point_to_polygon_distance(x,y,rings):
    """Positive distance if inside polygon, negative if outside."""
    min_d = min(point_segment_distance(x,y,*r[i],*r[i+1])
                for r in rings for i in range(len(r)-1))
    return min_d if point_in_multipolygon((x,y),rings) else -min_d

class Cell:
    """Cell used in polylabel refinement."""
    __slots__=("x","y","h","d","max")
    def __init__(self,x,y,h,d):
        self.x,self.y,self.h,self.d=x,y,h,d
        self.max=d+h*math.sqrt(2)
    def __lt__(self,o): return self.max>o.max

def polylabel(rings, precision=1e-6):
    """Find visual center of polygon using Mapbox polylabel algorithm."""
    pts=[p for r in rings for p in r[:-1]]
    if not pts: return None
    minx,maxx=min(p[0] for p in pts),max(p[0] for p in pts)
    miny,maxy=min(p[1] for p in pts),max(p[1] for p in pts)
    cell_size=min(maxx-minx,maxy-miny); h=cell_size/2
    # initial best = bbox center
    cx,cy=(minx+maxx)/2,(miny+maxy)/2
    best=Cell(cx,cy,0,point_to_polygon_distance(cx,cy,rings))
    # candidate queue
    pq=[]
    x=minx
    while x<maxx:
        y=miny
        while y<maxy:
            cx,cy=x+h,y+h
            c=Cell(cx,cy,h,point_to_polygon_distance(cx,cy,rings))
            if c.d>best.d: best=c
            heapq.heappush(pq,(-c.max,c))
            y+=cell_size
        x+=cell_size
    # refine
    while pq:
        _,c=heapq.heappop(pq)
        if c.max-best.d<=precision: continue
        h=c.h/2
        for dx in (-h,h):
            for dy in (-h,h):
                cx,cy=c.x+dx,c.y+dy
                nc = Cell(cx,cy,h,point_to_polygon_distance(cx,cy,rings))
                if nc.d > best.d: best=nc
                heapq.heappush(pq,(-nc.max,nc))
    return (best.x,best.y)

# Floor helpers
def parse_int(tags, keys):
    for k in keys:
        if k in tags:
            try: return int(tags[k])
            except: pass
    return None

def floors_from_levels(tags):
    """Generate floor labels from building:levels and underground levels."""
    above=parse_int(tags,["building:levels","levels"])
    below=parse_int(tags,["building:levels:underground","levels:underground","min_level"])
    below=abs(below) if below and below<0 else below
    floors=[]
    if below: floors+=[chr(ord("A")+i) for i in range(below-1,-1,-1)]
    if above: floors+=[str(i) for i in range(1,above+1)]
    return floors

# OSM parsing
tree=ET.parse(OSM_FILE); root=tree.getroot()

# Collect nodes and node tags
nodes, node_tags={}, {}
for n in root.findall("node"):
    nid=n.attrib.get("id")
    if "lat" in n.attrib and "lon" in n.attrib:
        nodes[nid]=(float(n.attrib["lat"]),float(n.attrib["lon"]))
    tags={t.attrib["k"]:t.attrib["v"] for t in n.findall("tag") if "k" in t.attrib}
    if tags: node_tags[nid]=tags

# Collect ways
ways_by_id={}
for w in root.findall("way"):
    wid=w.attrib["id"]
    nds=[nd.attrib["ref"] for nd in w.findall("nd") if "ref" in nd.attrib]
    tags={t.attrib["k"]:t.attrib["v"] for t in w.findall("tag") if "k" in t.attrib}
    ways_by_id[wid]={"nodes":nds,"tags":tags}

# Collect relations
relations=[]
for r in root.findall("relation"):
    rid=r.attrib["id"]
    tags={t.attrib["k"]:t.attrib["v"] for t in r.findall("tag") if "k" in t.attrib}
    members=[{"type":m.attrib.get("type",""),"ref":m.attrib.get("ref",""),"role":m.attrib.get("role","")} for m in r.findall("member")]
    relations.append({"id":rid,"tags":tags,"members":members})

# Entrance nodes
entrance_nodes={nid for nid,t in node_tags.items() if "entrance" in t or "door" in t}

# Shape builders
def shape_from_way(wid):
    """Convert a way into shape dict and coordinate ring."""
    w=ways_by_id.get(wid)
    if not w: return None,[],[]
    coords,node_ids=[],[]
    for nid in w["nodes"]:
        if nid in nodes:
            lat,lon=nodes[nid]
            coords.append((lon,lat)); node_ids.append(nid)
    if len(coords)<3: return None,[],[]
    ring=close_ring(coords)
    shape=[{"latitude":y,"longitude":x} for x,y in ring]
    return shape, ring, node_ids

def hull_from_rings(rings):
    pts=[p for r in rings for p in r[:-1]]
    return convex_hull(pts) if len(pts)>=3 else close_ring(pts)

# Building assembly
def assemble_entry(osm_id, code, name, defaultFloor, tags, shapes, rings, way_nodesets):
    """Assemble one building entry with all fields."""
    label=polylabel(rings) or polygon_area_and_centroid(rings[0])[1:]
    cx,cy=label
    hull=hull_from_rings(rings)
    floors=floors_from_levels(tags)

    # collect entrances on boundary and interior
    boundary=set().union(*way_nodesets)
    entrances={nid for nid in boundary if nid in entrance_nodes}
    for nid in entrance_nodes-boundary:
        if nid in nodes:
            lat,lon=nodes[nid]
            if point_in_multipolygon((lon,lat),rings): entrances.add(nid)

    return {
        "name": name,
        "osmId": str(osm_id),
        "floors": floors,
        "defaultFloor": str(defaultFloor),
        "labelPosition": {"latitude":cy,"longitude":cx},
        "shapes": shapes,
        "hitbox": [{"latitude":y,"longitude":x} for x,y in hull],
        "code": code,
        "entrances": [str(e) for e in sorted(entrances)]
    }

# Collect buildings
buildings, outer_ways_used={}, set()

# Relations (multipolygon buildings)
for rel in relations:
    if "building" not in rel["tags"]: continue
    osm_id = rel["id"]
    if osm_id in osm_id_to_info:
        info = osm_id_to_info[osm_id]
        outer=[m["ref"] for m in rel["members"] if m["type"]=="way" and m.get("role")=="outer"]
        if not outer: outer=[m["ref"] for m in rel["members"] if m["type"]=="way"]
        shapes,rings,nodesets=[],[],[]
        for wid in outer:
            shape,ring,nids=shape_from_way(wid)
            if shape: shapes.append(shape); rings.append(ring); nodesets.append(set(nids)); outer_ways_used.add(wid)
        if shapes:
            entry=assemble_entry(osm_id, info["code"], info["name"], info["defaultFloor"], rel["tags"],shapes,rings,nodesets)
            buildings[entry["code"]]=entry

# Standalone ways (not already used)
for wid,w in ways_by_id.items():
    if "building" not in w["tags"] or wid in outer_ways_used: continue
    if wid in osm_id_to_info:
        info = osm_id_to_info[wid]
        shape,ring,nids=shape_from_way(wid)
        if shape:
            entry=assemble_entry(wid, info["code"], info["name"], info["defaultFloor"], w["tags"],[shape],[ring],[set(nids)])
            buildings[entry["code"]]=entry

# Write JSON
with open(PARSED_DATA_OUTPUT_JSON,"w") as f: json.dump(buildings,f,indent=4)
print(f"Saved {len(buildings)} buildings to {PARSED_DATA_OUTPUT_JSON}")
analyze_missing_buildings()