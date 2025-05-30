from app.services.storage.factory import get_storage
from app.core.session import session_map
from app.core.config import settings
import os
import boto3

class FileService:
    def __init__(self):
        self.storage = get_storage()

    async def save_chunk(self, upload_session_id: str, chunk_index: int, chunk_data: bytes):
        return await self.storage.save_chunk(upload_session_id, chunk_index, chunk_data)

    async def merge_chunks(self, upload_session_id: str, total_chunks: int, merged_file_path: str):
        return await self.storage.merge_chunks(upload_session_id, total_chunks, merged_file_path)

    async def upload_file(self, file_path: str, s3_key: str):
        return await self.storage.upload_file(file_path, s3_key)

    async def delete_file(self, file_path_or_key: str):
        return await self.storage.delete_file(file_path_or_key)

    async def cleanup_session(self, upload_session_id: str):
        return await self.storage.cleanup_session(upload_session_id)

    def list_user_files(self, user_id: str):
        files = []
        if settings.STORAGE_BACKEND == "s3":
            # List S3 objects with prefix user_id/
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.S3_ACCESS_KEY,
                aws_secret_access_key=settings.S3_SECRET_KEY,
                endpoint_url=settings.S3_ENDPOINT_URL,
                region_name=settings.S3_REGION_NAME
            )
            paginator = s3_client.get_paginator('list_objects_v2')
            prefix = f"{user_id}/"
            for page in paginator.paginate(Bucket=settings.S3_BUCKET_NAME, Prefix=prefix):
                for obj in page.get('Contents', []):
                    file_url = f"{settings.S3_ENDPOINT_URL}/{settings.S3_BUCKET_NAME}/{obj['Key']}"
                    files.append(file_url)
        else:
            user_dir = os.path.join(settings.LOCAL_TEMP_CHUNK_PATH, "final", user_id)
            if os.path.exists(user_dir):
                for file_id in os.listdir(user_dir):
                    file_path = os.path.join(user_dir, file_id)
                    if os.path.isfile(file_path):
                        files.append(file_path)
        return files

    def check_user_access(self, upload_session_id: str, user_id: str, main_service_file_id: int = None):
        session = session_map.get(upload_session_id)
        if not session or session["user_id"] != user_id:
            return False
        if main_service_file_id is not None and session["main_service_file_id"] != main_service_file_id:
            return False
        return True

file_service = FileService() 