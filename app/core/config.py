from pydantic import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    MAIN_SERVICE_JWT_PUBLIC_KEY: str
    JWT_ALGORITHM: str = "RS256"
    EXPECTED_JWT_ISSUER: str
    EXPECTED_JWT_AUDIENCE: str

    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
    S3_BUCKET_NAME: str
    S3_ENDPOINT_URL: str
    S3_REGION_NAME: Optional[str] = None

    LOCAL_TEMP_CHUNK_PATH: Optional[str] = "/tmp/hayula_chunks"

    class Config:
        env_file = ".env"

settings = Settings() 