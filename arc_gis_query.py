from arcgis.gis import GIS
import json

portal = GIS()

parcel_layer_item = portal.content.get("0a8e645dc06d43f1b197b2ea2c2b876e")

parcel_layer = parcel_layer_item.layers[0]

where_clause = "ZIP = 15213"

fields = ["Building_ID", "Long_Name", "Short_Name", "Sign_Abbrev",
          "BuildingID_Numeric_2", "Floor_Count", "Building_Address"]

results = parcel_layer.query(
    where=where_clause,
    out_fields=fields,
)

def clean(val):
    return val.strip() if isinstance(val, str) else val

# Filter attributes to only the fields we want
data = {
    "features": [
        {
            "attributes": {k: clean(f.attributes.get(k)) for k in fields}
        }
        for f in results.features
    ]
}

with open("query.json", "w") as f:
    json.dump(data, f, indent=2)
print(f"Results saved to query.json ({len(data['features'])} features)")
