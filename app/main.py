from fastapi import FastAPI
from app.api.endpoints.upload import router as upload_router
from app.core.config import settings

app = FastAPI(
    title="Hayula Upload Service",
    version="1.0.0",
    openapi_url=None if settings.ENV == "production" else f"/openapi.json",
    docs_url=None if settings.ENV == "production" else f"/docs",
    redoc_url=None if settings.ENV == "production" else f"/redoc"
)
app.include_router(upload_router, prefix="/upload", tags=["upload"]) 