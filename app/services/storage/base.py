from abc import ABC, abstractmethod
from typing import Optional

class BaseStorage(ABC):
    @abstractmethod
    async def save_chunk(self, upload_session_id: str, chunk_index: int, chunk_data: bytes) -> str:
        pass

    @abstractmethod
    async def merge_chunks(self, upload_session_id: str, total_chunks: int, merged_file_path: str) -> str:
        pass

    @abstractmethod
    async def upload_file(self, file_path: str, s3_key: str) -> str:
        pass

    @abstractmethod
    async def delete_file(self, file_path_or_key: str, storage_type: Optional[str] = None) -> None:
        pass

    @abstractmethod
    async def cleanup_session(self, upload_session_id: str) -> None:
        pass
