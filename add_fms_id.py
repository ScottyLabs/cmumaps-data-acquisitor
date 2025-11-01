"""
Populate downloaded_buildings.json with FMS identifiers.

The script loads the building metadata and the previously generated
sign_abbrev_mapping.json, inserts an integer `fmsId` (sourced from
`BuildingID_Numeric_2`) right after each building's `osmId`, and reports how
many buildings were updated in the terminal.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import OrderedDict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: dict) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=4, ensure_ascii=False)
        handle.write("\n")


def candidate_labels(code: Optional[str], name: Optional[str]) -> Iterable[str]:
    """Generate potential lookup keys for the mapping."""
    seen = OrderedDict()

    def push(value: Optional[str]) -> None:
        if not value:
            return
        cleaned = value.strip()
        if cleaned and cleaned not in seen:
            seen[cleaned] = None

    push(code)
    if code:
        push(code.upper())

    if name:
        push(name)
        push(name.upper())
        tokens = [tok for tok in re.split(r"[^A-Za-z0-9]+", name.upper()) if tok]
        if tokens:
            push(tokens[0])
        if len(tokens) > 1:
            push("".join(tokens[:2]))

    return seen.keys()


def lookup_fms_id(
    mapping_upper: Dict[str, Dict[str, int]],
    code: Optional[str],
    name: Optional[str],
) -> Optional[int]:
    """Return the BuildingID_Numeric_2 using sign_abbrev_mapping."""
    for label in candidate_labels(code, name):
        entry = mapping_upper.get(label.upper())
        if entry:
            return entry["BuildingID_Numeric_2"]
    return None


def insert_fms_field(building: Dict[str, object], fms_id: int) -> Dict[str, object]:
    """Insert fmsId immediately after osmId in the given building record."""
    updated = OrderedDict()
    for key, value in building.items():
        updated[key] = value
        if key == "osmId":
            updated["fmsId"] = fms_id
    if "osmId" not in updated and "fmsId" not in updated:
        updated["fmsId"] = fms_id
    return updated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add fmsId to downloaded buildings using sign_abbrev_mapping.json.")
    parser.add_argument(
        "--buildings",
        type=Path,
        default=Path("downloaded_buildings.json"),
        help="Path to the downloaded buildings JSON (default: downloaded_buildings.json).",
    )
    parser.add_argument(
        "--mapping",
        type=Path,
        default=Path("sign_abbrev_mapping.json"),
        help="Path to sign_abbrev_mapping JSON (default: sign_abbrev_mapping.json).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute updates without writing changes.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    mapping = load_json(args.mapping)
    buildings = load_json(args.buildings)
    mapping_upper = {key.upper(): value for key, value in mapping.items()}

    updated_buildings: Dict[str, Dict[str, object]] = OrderedDict()
    added = 0
    already_present = 0
    missing: List[Tuple[str, str]] = []

    for code, payload in buildings.items():
        fms_id = lookup_fms_id(mapping_upper, payload.get("code") or code, payload.get("name"))
        has_fms = "fmsId" in payload

        if fms_id is not None:
            if has_fms and payload["fmsId"] == fms_id:
                already_present += 1
                updated_buildings[code] = payload
            else:
                updated_buildings[code] = insert_fms_field(payload, fms_id)
                added += 1 if not has_fms else 0
        else:
            if has_fms:
                already_present += 1
                updated_buildings[code] = payload
            else:
                missing.append((code, payload.get("name", "")))
                updated_buildings[code] = payload

    if not args.dry_run:
        write_json(args.buildings, updated_buildings)

    total = len(buildings)
    print(f"Processed {total} buildings.")
    print(f"Added fmsId to {added} buildings.")
    print(f"{already_present} buildings already had fmsId or no update was needed.")
    if missing:
        print(f"Unable to find mapping for {len(missing)} buildings:")
        for code, name in missing:
            print(f" - {code}: {name}")


if __name__ == "__main__":
    main()
