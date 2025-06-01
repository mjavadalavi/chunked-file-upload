from fastapi import FastAPI
from app.api.endpoints.files import router as files_router
from app.core.config import settings
from app.core.security import file_access_middleware

app = FastAPI(
    title="Upload Service",
    version="1.0.0",
    openapi_url=None if settings.ENV == "production" else f"/openapi.json",
    docs_url=None if settings.ENV == "production" else f"/docs",
    redoc_url=None if settings.ENV == "production" else f"/redoc"
)

# Adding middleware for file access check
app.middleware("http")(file_access_middleware)

app.include_router(files_router, prefix="/files", tags=["files"]) 