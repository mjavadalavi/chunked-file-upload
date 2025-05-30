import os
import shutil
import asyncio
import boto3
from typing import Optional
from .base import BaseStorage
from app.core.config import settings
from botocore.exceptions import BotoCoreError, ClientError

class S3Storage(BaseStorage):
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            endpoint_url=settings.S3_ENDPOINT_URL,
            region_name=settings.S3_REGION_NAME
        )

    async def save_chunk(self, upload_session_id: str, chunk_index: int, chunk_data: bytes) -> str:
        base_path = os.path.join(settings.LOCAL_TEMP_CHUNK_PATH, upload_session_id)
        await asyncio.to_thread(os.makedirs, base_path, True)
        chunk_path = os.path.join(base_path, f"chunk_{chunk_index}")
        await asyncio.to_thread(self._write_file, chunk_path, chunk_data)
        return chunk_path

    def _write_file(self, path, data):
        with open(path, "wb") as f:
            f.write(data)

    async def merge_chunks(self, upload_session_id: str, total_chunks: int, merged_file_path: str) -> str:
        base_path = os.path.join(settings.LOCAL_TEMP_CHUNK_PATH, upload_session_id)
        await asyncio.to_thread(self._merge_files, base_path, total_chunks, merged_file_path)
        return merged_file_path

    def _merge_files(self, base_path, total_chunks, merged_file_path):
        with open(merged_file_path, "wb") as merged:
            for i in range(total_chunks):
                chunk_path = os.path.join(base_path, f"chunk_{i}")
                with open(chunk_path, "rb") as chunk_file:
                    shutil.copyfileobj(chunk_file, merged)

    async def upload_file(self, file_path: str, s3_key: str) -> str:
        await asyncio.to_thread(self._upload_to_s3, file_path, s3_key)
        return s3_key

    def _upload_to_s3(self, file_path, s3_key):
        try:
            self.s3_client.upload_file(file_path, settings.S3_BUCKET_NAME, s3_key)
        except (BotoCoreError, ClientError) as e:
            raise Exception(f"S3 upload failed: {e}")

    async def delete_file(self, file_path_or_key: str, storage_type: Optional[str] = None) -> None:
        # file_path_or_key is the S3 key
        await asyncio.to_thread(self._delete_from_s3, file_path_or_key)

    def _delete_from_s3(self, s3_key):
        try:
            self.s3_client.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=s3_key)
        except (BotoCoreError, ClientError) as e:
            pass  # Optionally log

    async def cleanup_session(self, upload_session_id: str) -> None:
        base_path = os.path.join(settings.LOCAL_TEMP_CHUNK_PATH, upload_session_id)
        await asyncio.to_thread(self._delete_dir, base_path)

    def _delete_dir(self, path):
        if os.path.exists(path):
            shutil.rmtree(path) 