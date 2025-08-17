from minio import Minio
from dotenv import load_dotenv
import os

load_dotenv()

access_key = os.getenv("S3_ACCESS_KEY")
secret_key = os.getenv("S3_SECRET_KEY")
s3_endpoint = os.getenv("S3_ENDPOINT")

# Create client with access and secret key.
client = Minio(
    s3_endpoint,
    access_key=access_key,
    secret_key=secret_key,
)

bucket_name = "cmumaps"

# Check if bucket exists
print(f"Bucket '{bucket_name}' exists: {client.bucket_exists(bucket_name)}")


def upload_json_file(local_file_path, s3_object_name):
    """Upload a JSON file to S3 bucket"""
    try:
        # Upload the file
        client.fput_object(
            bucket_name,
            s3_object_name,
            local_file_path,
            content_type="application/json",
        )
        print(f"Successfully uploaded {local_file_path} as {s3_object_name}")
        return True
    except Exception as e:
        print(f"Error uploading {local_file_path}: {e}")
        return False


def list_bucket_objects():
    """List all objects in the bucket"""
    try:
        objects = client.list_objects(bucket_name, recursive=True)
        print(f"\nObjects in bucket '{bucket_name}':")
        for obj in objects:
            print(f"  - {obj.object_name} ({obj.size} bytes)")
    except Exception as e:
        print(f"Error listing objects: {e}")


# List existing objects
list_bucket_objects()

# Upload JSON files
json_files = [
    ("cmumaps-data/floorplans/all-graph.json", "floorplans/all-graph.json"),
    ("cmumaps-data/floorplans/buildings.json", "floorplans/buildings.json"),
    ("cmumaps-data/floorplans/floorplans.json", "floorplans/floorplans.json"),
    ("cmumaps-data/floorplans/placements.json", "floorplans/placements.json"),
]

print("\nUploading JSON files...")
for local_path, s3_path in json_files:
    if os.path.exists(local_path):
        upload_json_file(local_path, s3_path)
    else:
        print(f"File not found: {local_path}")

# List objects again to see the uploaded files
print("\nAfter upload:")
list_bucket_objects()
