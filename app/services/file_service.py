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
            # برای local storage، URL های دانلود پذیر برمی‌گردونیم
            user_dir = os.path.join(settings.PERSISTENT_LOCAL_STORAGE_PATH, "final", user_id)
            if os.path.exists(user_dir):
                for file_id in os.listdir(user_dir):
                    file_id_path = os.path.join(user_dir, file_id)
                    if os.path.isdir(file_id_path):  # file_id یک دایرکتوری هست
                        # URL دانلود پذیر برای این فایل می‌سازیم
                        download_url = f"{settings.UPLOAD_SERVICE_BASE_URL}/upload/download/{file_id}"
                        files.append(download_url)
        return files

    def check_user_access(self, upload_session_id: str, user_id: str, main_service_file_id: int = None):
        session = session_map.get(upload_session_id)
        if not session or session["user_id"] != user_id:
            return False
        if main_service_file_id is not None and session["main_service_file_id"] != main_service_file_id:
            return False
        return True

    async def delete_user_file(self, user_id: str, file_id: int):
        """
        حذف فایل کاربر بر اساس user_id و file_id
        """
        if settings.STORAGE_BACKEND == "s3":
            # برای S3، ممکنه چندین فایل با prefix user_id/file_id/ باشه
            # پس همه رو پیدا می‌کنیم و حذف می‌کنیم
            files = self.list_user_files(user_id)
            target_pattern = f"/{user_id}/{file_id}/"
            deleted_count = 0
            
            for file_url in files:
                if target_pattern in file_url:
                    # استخراج S3 key از URL
                    parts = file_url.split('/')
                    bucket_index = parts.index(settings.S3_BUCKET_NAME)
                    s3_key = '/'.join(parts[bucket_index + 1:])
                    await self.storage.delete_file(s3_key)
                    deleted_count += 1
            
            return deleted_count > 0
        else:
            # برای local storage، کل دایرکتوری file_id رو حذف می‌کنیم
            file_dir = os.path.join(settings.PERSISTENT_LOCAL_STORAGE_PATH, "final", user_id, str(file_id))
            if os.path.exists(file_dir):
                # حذف کل دایرکتوری (شامل همه فایل‌هاش)
                import shutil
                shutil.rmtree(file_dir)
                return True
            return False

file_service = FileService() 