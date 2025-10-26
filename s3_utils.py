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


def upload_folder(local_folder_path, s3_folder_name, file_type="octet-stream"):
    """
    Upload a folder to S3 bucket

    Args:
        local_folder_path (str): The local object name/path
        s3_folder_name (str): The S3 object name/path
        file_type (str): the file type
    """
    try:
        # Upload each of the files in the folder
        for filename in os.listdir(local_folder_path):
            local_path = os.path.join(local_folder_path, filename)
            if os.path.isdir(local_path):  # only upload files in the folder
                continue
            s3_object_name = f"{s3_folder_name}/{filename}"
            client.fput_object(
                bucket_name,
                s3_object_name,
                local_path,
                content_type=f"application/{file_type}",
            )
        print(f"Successfully uploaded {local_folder_path} as {s3_folder_name}")
        return True
    except Exception as e:
        print(f"Error uploading {local_folder_path}: {e}")
        return False


def upload_generic_file(local_file_path, s3_object_name, file_type="octet-stream"):
    """Upload a JSON file to S3 bucket

    Args:
        local_file_path (str): The local object name/path
        s3_object_name (str): The S3 object name/path
        file_type (str): the file type
    """
    try:
        # Upload the file
        client.fput_object(
            bucket_name,
            s3_object_name,
            local_file_path,
            content_type=f"application/{file_type}",
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


def get_generic_file_from_s3(s3_object_name):
    """
    Get generic data from S3 bucket

    Args:
        s3_object_name (str): The S3 object name/path
        return_data (bool): If True, return the data as Python object
                           If False, return the raw response object

    Returns:
        response object
    """
    try:
        # Get the object
        response = client.get_object(bucket_name, s3_object_name)
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
