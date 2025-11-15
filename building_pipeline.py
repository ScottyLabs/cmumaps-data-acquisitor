"""
End-to-end pipeline for generating CMU building data with FMS identifiers.

This script stitches together the three existing stages:
  1. Parse an OSM export into `parsed_buildings.json` using osm_building_to_json.py.
  2. Build the signage abbreviation mapping using sign_abbrev_mapping.py.
  3. Add FMS IDs to the parsed buildings via add_fms_id.py.

How the building pipeline works: osm_building_to_json takes an OSM file and converts it into a set of downloaded buildings that follow the structure of downloaded_buildings.json. After that, you run sign_abbrev_mapping.py to generate a mapping from each building's name to its FMS ID, which comes from query.json that you download with GIS building. Finally, you run add_fms_id to attach the correct FMS ID from the mapping to each building parsed from the OSM file.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional, Sequence


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the building parsing pipeline from OSM extraction to FMS IDs."
    )
    parser.add_argument(
        "--osm-file",
        type=Path,
        default=Path("export.osm"),
        help="Path to the source OSM file (default: export.osm).",
    )
    parser.add_argument(
        "--downloaded-buildings",
        type=Path,
        default=Path("downloaded_buildings.json"),
        help="Path to downloaded_buildings.json (default: downloaded_buildings.json).",
    )
    parser.add_argument(
        "--building-info-map",
        type=Path,
        default=Path("building_info_map.json"),
        help="Output path for building_info_map.json (default: building_info_map.json).",
    )
    parser.add_argument(
        "--parsed-buildings",
        type=Path,
        default=Path("parsed_buildings.json"),
        help="Output path for parsed_buildings.json (default: parsed_buildings.json).",
    )
    parser.add_argument(
        "--query-json",
        type=Path,
        default=Path("query.json"),
        help="Path to the ArcGIS export used for the sign abbreviation mapping (default: query.json).",
    )
    parser.add_argument(
        "--sign-mapping",
        type=Path,
        default=Path("sign_abbrev_mapping.json"),
        help="Output path for the sign abbreviation mapping (default: sign_abbrev_mapping.json).",
    )
    parser.add_argument(
        "--python",
        type=Path,
        default=Path(sys.executable),
        help="Python interpreter to use when invoking the component scripts (default: current interpreter).",
    )
    parser.add_argument(
        "--osm-script",
        type=Path,
        default=Path("osm_building_to_json.py"),
        help="Path to osm_building_to_json.py (default: osm_building_to_json.py).",
    )
    parser.add_argument(
        "--sign-script",
        type=Path,
        default=Path("sign_abbrev_mapping.py"),
        help="Path to sign_abbrev_mapping.py (default: sign_abbrev_mapping.py).",
    )
    parser.add_argument(
        "--fms-script",
        type=Path,
        default=Path("add_fms_id.py"),
        help="Path to add_fms_id.py (default: add_fms_id.py).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Propagate the --dry-run flag to add_fms_id.py (does not rewrite parsed_buildings.json).",
    )
    return parser.parse_args()


def _ensure_exists(path: Path, description: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Could not find {description}: {path}")


def _run_step(step_name: str, cmd: Sequence[str], env: Optional[Dict[str, str]] = None) -> None:
    print(f"\n[Pipeline] {step_name}")
    print(f"          Command: {' '.join(cmd)}")
    subprocess.run(cmd, check=True, env=env)


def main() -> None:
    args = parse_args()

    _ensure_exists(args.python, "Python interpreter")
    _ensure_exists(args.osm_script, "OSM parsing script")
    _ensure_exists(args.sign_script, "sign abbreviation script")
    _ensure_exists(args.fms_script, "add_fms script")
    _ensure_exists(args.osm_file, "OSM file")
    _ensure_exists(args.downloaded_buildings, "downloaded_buildings.json")
    _ensure_exists(args.query_json, "query.json")

    env = os.environ.copy()
    env.update(
        {
            "CMUMAPS_OSM_FILE": str(args.osm_file),
            "CMUMAPS_DOWNLOADED_BUILDINGS_JSON": str(args.downloaded_buildings),
            "CMUMAPS_BUILDING_MAPPING_OUTPUT": str(args.building_info_map),
            "CMUMAPS_PARSED_BUILDINGS_OUTPUT": str(args.parsed_buildings),
        }
    )

    _run_step(
        "Parsing OSM buildings",
        [str(args.python), str(args.osm_script)],
        env=env,
    )

    _run_step(
        "Generating sign abbreviation mapping",
        [
            str(args.python),
            str(args.sign_script),
            "--query",
            str(args.query_json),
            "--output",
            str(args.sign_mapping),
        ],
    )

    add_fms_cmd = [
        str(args.python),
        str(args.fms_script),
        "--buildings",
        str(args.parsed_buildings),
        "--mapping",
        str(args.sign_mapping),
    ]
    if args.dry_run:
        add_fms_cmd.append("--dry-run")

    _run_step("Attaching FMS IDs to parsed buildings", add_fms_cmd)

    print(
        "\n[Pipeline] Complete!\n"
        f"  Parsed buildings : {args.parsed_buildings}\n"
        f"  Sign mapping     : {args.sign_mapping}\n"
        f"  Building info map: {args.building_info_map}"
    )


if __name__ == "__main__":
    main()
