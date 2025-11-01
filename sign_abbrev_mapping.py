"""Create a mapping from CMU sign abbreviations to building identifiers.

The script walks the ArcGIS export stored in query.json and writes a JSON
mapping that associates each building's signage abbreviation (or short name
when the signage value is missing) with:
  - BuildingID_Numeric_2 saved as an int
  - Building_ID saved (as-is, preserving leading zeros) under the key
    `building_code`
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, Optional, Set, Union

MappingEntry = Dict[str, Union[int, str]]
MappingResult = Dict[str, MappingEntry]


def _normalize_label(sign_abbrev: Optional[str], short_name: Optional[str]) -> Optional[str]:
    """Return the preferred label for a building (Sign_Abbrev > Short_Name)."""
    if sign_abbrev:
        sign_abbrev = sign_abbrev.strip()
        if sign_abbrev:
            return sign_abbrev
    if short_name:
        short_name = short_name.strip()
        if short_name:
            return short_name
    return None


def _to_building_code(raw_value) -> Optional[str]:
    """Return the Building_ID value while keeping any leading zeros."""
    if raw_value is None:
        return None
    value = str(raw_value).strip()
    return value or None


def _to_building_numeric(raw_value) -> Optional[int]:
    """Convert BuildingID_Numeric_2 to an int."""
    if raw_value is None:
        return None
    text = str(raw_value).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def build_sign_mapping(features: Iterable[dict]) -> MappingResult:
    """Construct the sign abbreviation mapping."""
    grouped: MappingResult = {}
    sign_to_ids: Dict[str, Set[str]] = defaultdict(set)

    for feature in features:
        attributes = feature.get("attributes") or {}
        sign_label = _normalize_label(attributes.get("Sign_Abbrev"), None)
        if sign_label:
            building_id = _to_building_numeric(attributes.get("BuildingID_Numeric_2"))
            if building_id is not None:
                sign_to_ids[sign_label].add(building_id)

    conflict_signs = {sign for sign, ids in sign_to_ids.items() if len(ids) > 1}

    for feature in features:
        attributes = feature.get("attributes") or {}
        sign_label = _normalize_label(attributes.get("Sign_Abbrev"), None)
        short_label = _normalize_label(None, attributes.get("Short_Name"))

        label = None
        if sign_label:
            if sign_label in conflict_signs and short_label:
                label = short_label
            else:
                label = sign_label
        else:
            label = short_label

        if not label:
            continue

        building_id = _to_building_numeric(attributes.get("BuildingID_Numeric_2"))
        building_code = _to_building_code(attributes.get("Building_ID"))

        if building_id is None or building_code is None:
            continue

        entry: MappingEntry = {
            "BuildingID_Numeric_2": building_id,
            "building_code": building_code,
        }

        grouped[label] = entry

    return {label: grouped[label] for label in sorted(grouped)}


def load_query(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Could not find query JSON at {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build mapping from signage abbreviations to building identifiers.")
    parser.add_argument(
        "--query",
        type=Path,
        default=Path("query.json"),
        help="Path to the ArcGIS export (default: query.json in this directory).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("sign_abbrev_mapping.json"),
        help="Path to write the resulting JSON mapping (default: sign_abbrev_mapping.json).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data = load_query(args.query)
    features = data.get("features") or []

    mapping = build_sign_mapping(features)
    output = json.dumps(mapping, indent=2, ensure_ascii=False)

    args.output.write_text(output + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
