from app.core.config import settings
from .s3 import S3Storage
from .internal import InternalStorage
from .base import BaseStorage

_storage_instance = None

def get_storage() -> BaseStorage:
    global _storage_instance
    if _storage_instance is not None:
        return _storage_instance
    if settings.STORAGE_BACKEND == "s3":
        _storage_instance = S3Storage()
    elif settings.STORAGE_BACKEND == "local":
        _storage_instance = InternalStorage()
    else:
        raise ValueError(f"Unknown STORAGE_BACKEND: {settings.STORAGE_BACKEND}")
    return _storage_instance
