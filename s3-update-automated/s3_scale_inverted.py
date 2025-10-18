import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from s3_utils import get_json_from_s3, save_upload_json_file

file_path = "downloaded_placements.json"
placements = get_json_from_s3("floorplans/placements.json", return_data=True)


for key, value in placements.items():
    for floor_num, floor in value.items():
        # print(floor_num, floor["scale"])
        floor["scale"] = 1 / floor["scale"]


save_upload_json_file(
    s3_object_name="floorplans/placements.json",
    json_data=placements,
    cleanup_local=False,
    local_file_path=os.path.join("s3-update-automated", file_path),
)
