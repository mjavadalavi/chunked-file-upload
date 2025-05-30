import os
import shutil
import asyncio
from typing import Optional
from .base import BaseStorage
from app.core.config import settings

class InternalStorage(BaseStorage):
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
        # For local, just move/rename the file to a final location
        final_path = os.path.join(settings.LOCAL_TEMP_CHUNK_PATH, "final", s3_key)
        final_dir = os.path.dirname(final_path)
        await asyncio.to_thread(os.makedirs, final_dir, True)
        await asyncio.to_thread(shutil.move, file_path, final_path)
        return final_path

    async def delete_file(self, file_path_or_key: str, storage_type: Optional[str] = None) -> None:
        # file_path_or_key is a local path
        await asyncio.to_thread(self._delete_file, file_path_or_key)

    def _delete_file(self, file_path):
        if os.path.exists(file_path):
            os.remove(file_path)

    async def cleanup_session(self, upload_session_id: str) -> None:
        base_path = os.path.join(settings.LOCAL_TEMP_CHUNK_PATH, upload_session_id)
        await asyncio.to_thread(self._delete_dir, base_path)

    def _delete_dir(self, path):
        if os.path.exists(path):
            shutil.rmtree(path) 