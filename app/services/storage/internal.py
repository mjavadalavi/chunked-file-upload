import os
import shutil
import asyncio
import logging
import concurrent.futures
from typing import Optional
from .base import BaseStorage
from app.core.config import settings

logger = logging.getLogger(__name__)

# ایجاد یک ThreadPoolExecutor برای عملیات I/O بلاکینگ
thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)

class InternalStorage(BaseStorage):
    def _save_chunk_sync(self, upload_session_id: str, chunk_index: int, chunk_data: bytes) -> str:
        """ذخیره یک چانک به صورت سنکرون"""
        try:
            base_path = os.path.join(settings.LOCAL_TEMP_CHUNK_PATH, str(upload_session_id))
            
            # چک کنیم که path یک فایل نباشه
            if os.path.exists(base_path) and os.path.isfile(base_path):
                os.remove(base_path)
            
            os.makedirs(base_path, exist_ok=True)
            chunk_path = os.path.join(base_path, f"chunk_{chunk_index}")
            
            with open(chunk_path, "wb") as f:
                f.write(chunk_data)
            
            logger.debug(f"Chunk saved successfully: {chunk_path} ({len(chunk_data)} bytes)")
            return chunk_path
            
        except Exception as e:
            logger.error(f"Error saving chunk {chunk_index} for session {upload_session_id}: {str(e)}")
            raise

    async def save_chunk(self, upload_session_id: str, chunk_index: int, chunk_data: bytes) -> str:
        """ذخیره یک چانک به صورت غیربلاکینگ"""
        try:
            logger.debug(f"Saving chunk {chunk_index} for session {upload_session_id}")
            
            # استفاده از ThreadPoolExecutor برای اجرای عملیات I/O بلاکینگ
            loop = asyncio.get_event_loop()
            chunk_path = await loop.run_in_executor(
                thread_pool,
                self._save_chunk_sync,
                upload_session_id,
                chunk_index,
                chunk_data
            )
            
            return chunk_path
        except Exception as e:
            logger.error(f"Error in async save_chunk: {str(e)}")
            raise

    def _merge_files_sync(self, base_path: str, total_chunks: int, merged_file_path: str) -> dict:
        """ادغام چانک‌ها به یک فایل نهایی به صورت سنکرون"""
        try:
            # ایجاد directory برای merged file
            merged_dir = os.path.dirname(merged_file_path)
            os.makedirs(merged_dir, exist_ok=True)
            
            logger.info(f"Starting merge of {total_chunks} chunks from {base_path} to {merged_file_path}")
            total_size = 0
            chunks_merged = 0
            
            with open(merged_file_path, "wb") as merged:
                for i in range(total_chunks):
                    chunk_path = os.path.join(base_path, f"chunk_{i}")
                    
                    if not os.path.exists(chunk_path):
                        logger.warning(f"Chunk file not found: {chunk_path}")
                        continue
                    
                    chunk_size = os.path.getsize(chunk_path)
                    logger.debug(f"Processing chunk {i+1}/{total_chunks}: {chunk_path} ({chunk_size} bytes)")
                    
                    with open(chunk_path, "rb") as chunk_file:
                        chunk_data = chunk_file.read()
                        merged.write(chunk_data)
                        total_size += len(chunk_data)
                        chunks_merged += 1
                    
                    logger.debug(f"Chunk {i+1} merged successfully")
            
            logger.info(
                f"Merge completed:\n"
                f"- Chunks merged: {chunks_merged}/{total_chunks}\n"
                f"- Total size: {total_size/1024/1024:.2f}MB\n"
                f"- Output file: {merged_file_path}"
            )
            
            return {
                "chunks_merged": chunks_merged,
                "total_size": total_size,
                "success": chunks_merged == total_chunks
            }
            
        except Exception as e:
            logger.error(f"Error merging chunks: {str(e)}")
            # پاک کردن فایل خروجی ناقص
            if os.path.exists(merged_file_path):
                try:
                    os.remove(merged_file_path)
                    logger.info(f"Removed incomplete output file: {merged_file_path}")
                except:
                    pass
            raise

    async def merge_chunks(self, upload_session_id: str, total_chunks: int, merged_file_path: str) -> str:
        """ادغام چانک‌ها به یک فایل نهایی به صورت غیربلاکینگ"""
        try:
            base_path = os.path.join(settings.LOCAL_TEMP_CHUNK_PATH, upload_session_id)
            
            # استفاده از ThreadPoolExecutor برای اجرای عملیات I/O بلاکینگ
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                thread_pool,
                self._merge_files_sync,
                base_path,
                total_chunks,
                merged_file_path
            )
            
            # اطمینان از اینکه فایل به طور کامل نوشته شده است
            if result.get("success", False):
                # اضافه کردن تأخیر کوتاه برای اطمینان از اتمام عملیات I/O
                await asyncio.sleep(0.1)
                
                # بررسی مجدد فایل
                if os.path.exists(merged_file_path):
                    file_size = os.path.getsize(merged_file_path)
                    logger.info(f"Final file size verification: {file_size/1024/1024:.2f}MB")
                else:
                    logger.error(f"Final file does not exist after merge: {merged_file_path}")
                    raise FileNotFoundError(f"Merged file not created: {merged_file_path}")
            
            return merged_file_path
        except Exception as e:
            logger.error(f"Error in async merge_chunks: {str(e)}")
            raise

    async def upload_file(self, file_path: str, s3_key: str) -> str:
        # For local, just move/rename the file to a final location
        final_path = os.path.join(settings.PERSISTENT_LOCAL_STORAGE_PATH, "final", s3_key)
        final_dir = os.path.dirname(final_path)
        await asyncio.to_thread(os.makedirs, final_dir, exist_ok=True)
        await asyncio.to_thread(shutil.move, file_path, final_path)
        return final_path

    async def delete_file(self, file_path_or_key: str, storage_type: Optional[str] = None) -> None:
        # file_path_or_key is a local path
        await asyncio.to_thread(self._delete_file, file_path_or_key)

    def _delete_file(self, file_path):
        if os.path.exists(file_path):
            os.remove(file_path)

    def _cleanup_session_sync(self, upload_session_id: str) -> dict:
        """پاکسازی دایرکتوری چانک‌ها به صورت سنکرون"""
        try:
            base_path = os.path.join(settings.LOCAL_TEMP_CHUNK_PATH, upload_session_id)
            
            if os.path.exists(base_path):
                files = os.listdir(base_path)
                total_size = sum(os.path.getsize(os.path.join(base_path, f)) for f in files)
                
                logger.info(
                    f"Cleaning up chunk directory:\n"
                    f"- Path: {base_path}\n"
                    f"- Files: {len(files)}\n"
                    f"- Total size: {total_size/1024/1024:.2f}MB"
                )
                
                shutil.rmtree(base_path)
                logger.info(f"Cleanup completed for {base_path}")
                
                return {
                    "files_removed": len(files),
                    "total_size": total_size,
                    "success": True
                }
            
        except Exception as e:
            logger.error(f"Error cleaning up chunks: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def cleanup_session(self, upload_session_id: str) -> None:
        """پاکسازی دایرکتوری چانک‌ها به صورت غیربلاکینگ"""
        try:
            # استفاده از ThreadPoolExecutor برای اجرای عملیات I/O بلاکینگ
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                thread_pool,
                self._cleanup_session_sync,
                upload_session_id
            )
            
            return result
        except Exception as e:
            logger.error(f"Error in async cleanup_session: {str(e)}")
            raise 