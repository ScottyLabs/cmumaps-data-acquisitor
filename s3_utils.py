from minio import Minio
from dotenv import load_dotenv
import os
import json

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


def save_upload_json_file(
    s3_object_name: str,
    json_data: dict | list,
    local_file_path: str = None,
    indent: int = 2,
    ensure_ascii: bool = False,
    cleanup_local: bool = False,
) -> bool:
    """
    Save JSON data to a local file and upload it to S3 bucket

    Args:
        s3_object_name (str): The object name/path in S3 bucket
        json_data (dict | list): The JSON data to save and upload
        local_file_path (str, optional): Local file path. If None, uses s3_object_name
        indent (int): Number of spaces for JSON indentation (default: 2)
        ensure_ascii (bool): If True, escape non-ASCII characters (default: False)
        cleanup_local (bool): If True, delete local file after successful upload (default: False)

    Returns:
        bool: True if successful, False otherwise
    """
    # Use s3_object_name as local path if not specified
    local_path = local_file_path if local_file_path else s3_object_name

    try:
        # Save JSON data to local file with proper formatting
        with open(local_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=indent, ensure_ascii=ensure_ascii)
        print(f"Successfully saved JSON data to {local_path}")

    except (IOError, OSError) as e:
        print(f"Error saving file {local_path}: {e}")
        return False
    except (TypeError, ValueError) as e:
        print(f"Error serializing JSON data: {e}")
        return False

    try:
        # Upload the file to S3
        success = upload_json_file(local_path, s3_object_name)

        if success and cleanup_local and local_path != s3_object_name:
            # Clean up local file if requested and it's not the same as S3 name
            try:
                os.remove(local_path)
                print(f"Cleaned up local file {local_path}")
            except OSError as e:
                print(f"Warning: Could not delete local file {local_path}: {e}")

        return success

    except Exception as e:
        print(f"Error uploading {local_path} to S3: {e}")
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


def download_json_file(s3_object_name, local_file_path):
    """Download a JSON file from S3 bucket"""
    try:
        # Download the file
        client.fget_object(bucket_name, s3_object_name, local_file_path)
        print(f"Successfully downloaded {s3_object_name} to {local_file_path}")
        return True
    except Exception as e:
        print(f"Error downloading {s3_object_name}: {e}")
        return False


def get_json_from_s3(s3_object_name, return_data=False):
    """
    Get JSON data from S3 bucket

    Args:
        s3_object_name (str): The S3 object name/path
        return_data (bool): If True, return the JSON data as Python object
                           If False, return the raw response object

    Returns:
        dict/list: JSON data if return_data=True, otherwise response object
    """
    try:
        # Get the object
        response = client.get_object(bucket_name, s3_object_name)

        if return_data:
            # Read and parse JSON data
            json_data = json.loads(response.read().decode("utf-8"))
            response.close()
            print(f"Successfully retrieved JSON data from {s3_object_name}")
            return json_data
        else:
            print(f"Successfully retrieved object {s3_object_name}")
            return response

    except Exception as e:
        print(f"Error getting {s3_object_name}: {e}")
        return None


def list_json_files():
    """List all JSON files in the bucket"""
    try:
        objects = client.list_objects(bucket_name, recursive=True)
        json_files = []

        for obj in objects:
            if obj.object_name.endswith(".json"):
                json_files.append(
                    {
                        "name": obj.object_name,
                        "size": obj.size,
                        "last_modified": obj.last_modified,
                    }
                )

        print(f"\nJSON files in bucket '{bucket_name}':")
        for file_info in json_files:
            print(f"  - {file_info['name']} ({file_info['size']} bytes)")

        return json_files

    except Exception as e:
        print(f"Error listing JSON files: {e}")
        return []
