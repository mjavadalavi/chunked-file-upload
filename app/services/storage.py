import os
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from app.core.config import settings
import shutil

s3_client = boto3.client(
    's3',
    aws_access_key_id=settings.S3_ACCESS_KEY,
    aws_secret_access_key=settings.S3_SECRET_KEY,
    endpoint_url=settings.S3_ENDPOINT_URL,
    region_name=settings.S3_REGION_NAME
)

def save_chunk_locally(upload_session_id: str, chunk_index: int, chunk_data):
    base_path = os.path.join(settings.LOCAL_TEMP_CHUNK_PATH, upload_session_id)
    os.makedirs(base_path, exist_ok=True)
    chunk_path = os.path.join(base_path, f"chunk_{chunk_index}")
    with open(chunk_path, "wb") as f:
        f.write(chunk_data)
    return chunk_path

def merge_chunks(upload_session_id: str, total_chunks: int, merged_file_path: str):
    base_path = os.path.join(settings.LOCAL_TEMP_CHUNK_PATH, upload_session_id)
    with open(merged_file_path, "wb") as merged:
        for i in range(total_chunks):
            chunk_path = os.path.join(base_path, f"chunk_{i}")
            with open(chunk_path, "rb") as chunk_file:
                shutil.copyfileobj(chunk_file, merged)
    return merged_file_path

def upload_file_to_s3(file_path: str, s3_key: str):
    try:
        s3_client.upload_file(file_path, settings.S3_BUCKET_NAME, s3_key)
        return s3_key
    except (BotoCoreError, ClientError) as e:
        raise Exception(f"S3 upload failed: {e}")

def cleanup_local_session(upload_session_id: str):
    base_path = os.path.join(settings.LOCAL_TEMP_CHUNK_PATH, upload_session_id)
    if os.path.exists(base_path):
        shutil.rmtree(base_path)

def cleanup_file(file_path: str):
    if os.path.exists(file_path):
        os.remove(file_path) 