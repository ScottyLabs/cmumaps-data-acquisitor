"""
Pipeline: Fetch CMU floor-plan SVGs for a set of buildings.

Input JSON format (buildings.json):
[
  {
    "building": "CFA",
    "floorid": {
      "1": "EFC83720C0",
      "2": "D64D42B084",
      "3": "C54772993C",
      "4": "60BFC57E1E",
      "A": "268478AA5B",
      "AM": "96AB66D556",
      "M": "221BDC4DCC"
    }
  }
]
"""

import argparse
import json
from pathlib import Path
import re
import time
from typing import Dict, Any, List, Optional
import requests

ENDPOINT = "https://fmsystems.cmu.edu/FMInteract/tools/getDefaultLayersData.ashx"
DEFAULT_PARAMS = {
    "isRevit": "false",
    "RoomBoundaryLayer": "A-AREA",
    "RoomTagLayer": "A-AREA-IDEN",
}

# Paste your session cookies and headers here (copied from your browser)
cookies = {
}

headers = {
}

def slugify(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "building"

def read_buildings(path: str) -> List[Dict[str, Any]]:
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("buildings.json must be a JSON list of objects.")
    for obj in data:
        if not isinstance(obj, dict) or "building" not in obj or "floorid" not in obj:
            raise ValueError("Each item must be an object with 'building' and 'floorid'.")
        if not isinstance(obj["floorid"], dict):
            raise ValueError("'floorid' must be an object mapping floor labels to floor IDs.")
    return data

def fetch_svg(
    floor_id: str,
    svg_filename_param: str,
    out_file: Path,
    cookies: Dict[str, str],
    headers: Dict[str, str],
    timeout: float = 30.0,
    retries: int = 3,
    backoff: float = 1.5,
    verify_ssl: bool = False,
) -> bool:
    params = dict(DEFAULT_PARAMS)
    params["floorId"] = floor_id
    params["svgFile"] = svg_filename_param
    print(params)

    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(
                ENDPOINT,
                params=params,
                cookies=cookies,
                headers=headers,
                timeout=timeout,
                verify=verify_ssl,
            )
            if resp.status_code == 200 and resp.text.strip():
                out_file.parent.mkdir(parents=True, exist_ok=True)
                out_file.write_text(resp.text, encoding="utf-8")
                return True
            else:
                print(f"[warn] HTTP {resp.status_code} for floorId={floor_id}; attempt {attempt}/{retries}")
        except Exception as e:
            last_exc = e
            print(f"[warn] Exception on attempt {attempt}/{retries} for floorId={floor_id}: {e}")
        time.sleep(backoff ** (attempt - 1))
    if last_exc:
        print(f"[error] Failed for floorId={floor_id}: {last_exc}")
    return False

def main():
    ap = argparse.ArgumentParser(description="Fetch floor-plan SVGs for buildings/floorid.")
    ap.add_argument("--buildings", default="buildings.json", help="Path to buildings.json (list of {building, floorid})")
    ap.add_argument("--out", default="svg_files", help="Output root directory")
    ap.add_argument("--delay", type=float, default=0.0, help="Seconds to sleep between requests (politeness)")
    ap.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout per request in seconds")
    ap.add_argument("--retries", type=int, default=3, help="HTTP retries per request")
    ap.add_argument("--backoff", type=float, default=1.5, help="Exponential backoff base between retries")
    ap.add_argument("--verify-ssl", action="store_true", help="Verify SSL certificates (default: off)")

    args = ap.parse_args()

    buildings = read_buildings(args.buildings)
    out_root = Path(args.out)

    total = 0
    ok = 0

    # Mapping of building names to special curl param names
    BUILDING_NAME_OVERRIDES = {
        "an": "ansys",
        "ph": "bp",
        "br": "brh",
        "dithridge-street-garage": "dithgarage",
        "east-campus-garage": "ecg",
        "eds": "edsh",
        "fm": "fms",
        "mc": "fifth4721",
        "fifth-ave-4802-wqed": "wqed",
        "forbes-ave-4615-gatf": "frbs4615",
        "ghc": "gates",
        "gesling-stadium": "gef",
        "ini": "hnry4616",
        "henry-st-4618": "hnry4618",
        "henry-st-4620": "hnry4620",
        "highmark-center-for-health-wellness-athletics": "hmc",
        "hl": "hunt",
        "mm": "mmch",
        "nsh": "ns",
        "pc": "posner",
        "pos": "ph",
        "cic": "frbs4720",
        "sc": "scotthall",
        "south-craig-st-203": "scrg203",
        "2sc": "scrg205",
        "3sc": "scrg300",
        "south-craig-st-311": "scrg311",
        "4sc": "scrg407",
        "cc": "scrg417",
        "south-neville-st-485": "snev485",
        "tcs": "tcshall",
        "tep": "tsb",
        "ut": "utdc",
    }

    for building in buildings:
        building_name = building["building"]
        floorids: Dict[str, str] = building["floorid"]
        folder = out_root / slugify(building_name)

        for floor_num, floor_id in floorids.items():
            total += 1
            out_file = folder / f"{floor_num}.svg"
            floor_label = str(floor_num).strip()

            building_name_slug = slugify(building_name)
            param_building_name = BUILDING_NAME_OVERRIDES.get(building_name_slug, building_name_slug)

            # special cases since the school's official data is inconsistent in their curl param
            suffix = "fesim" if (building_name_slug == "an" and floor_label.lower() == "d") else "esim"
            suffix = "fmsystems" if (building_name_slug == "fifth-ave-4802-wqed" and floor_label.lower() == "1") else suffix
            suffix = "fmsystems" if (building_name_slug == "pos") else suffix
            suffix = "fmsystems" if (building_name_slug == "sc") else suffix
            suffix = "fmsystems" if (building_name_slug == "cic" and floor_label.lower() == "4") else suffix
            suffix = "fmsystems" if (building_name_slug == "weh" and floor_label.lower() != "5" and floor_label.lower() != "9") else suffix
            
            svg_filename_param = f"{param_building_name}-{floor_label.lower()}-{suffix}.svg"

            print(f"[fetch] {building_name} | floor {floor_num} -> {out_file.name} (id={floor_id})")

            success = fetch_svg(
                floor_id=floor_id,
                svg_filename_param=svg_filename_param,
                out_file=out_file,
                cookies=cookies,
                headers=headers,
                timeout=args.timeout,
                retries=args.retries,
                backoff=args.backoff,
                verify_ssl=args.verify_ssl,
            )
            if success:
                ok += 1
                print(f"[ok] Saved -> {out_file}")
            else:
                print(f"[fail] Could not fetch floor {floor_num} (id={floor_id}) for {building_name}")

            if args.delay > 0:
                time.sleep(args.delay)

    print(f"\nDone. {ok}/{total} SVGs saved under: {out_root.resolve()}")

if __name__ == "__main__":
    main()
