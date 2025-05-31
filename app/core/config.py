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

    LOCAL_TEMP_CHUNK_PATH: Optional[str] = "/tmp/hayula_chunks"
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