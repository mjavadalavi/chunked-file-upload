from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    ENV: str = "local"
    
    MAIN_SERVICE_JWT_PUBLIC_KEY: str
    JWT_ALGORITHM: str = "RS256"
    EXPECTED_JWT_ISSUER: str
    EXPECTED_JWT_AUDIENCE: str

    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET_NAME: str = "hayula-uploads"
    S3_ENDPOINT_URL: str = ""
    S3_REGION_NAME: Optional[str] = None

    # Local Temporary Storage for Chunks (Optional, if not using direct S3 multipart)
    LOCAL_TEMP_CHUNK_PATH: str = "/tmp/hayula_chunks"

    # Persistent Local Storage for completed files (if not using S3 as primary)
    PERSISTENT_LOCAL_STORAGE_PATH: str = "/var/data/hayula_uploads" # Example, make sure this path is writable by the service
    UPLOAD_SERVICE_BASE_URL: str = "http://localhost:8000" # Or your actual service URL

    STORAGE_BACKEND: str = "local"  # 's3' or 'local'
    SERVICE_PORT: int = 8000

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env" if ENV == "local" else None,
        env_file_encoding="utf-8",
        env_nested_delimiter="_",
        env_nested_settings=True,
    )

settings = Settings() 