import logging
from fastapi import FastAPI
from app.api.endpoints.files import router as files_router
from app.core.config import settings
from app.core.security import file_access_middleware
from fastapi.middleware.cors import CORSMiddleware

# تنظیم logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(
    title="Hayula Upload Service",
    version="1.0.0",
    openapi_url=None if settings.ENV == "production" else f"/openapi.json",
    docs_url=None if settings.ENV == "production" else f"/docs",
    redoc_url=None if settings.ENV == "production" else f"/redoc"
)

# Adding middleware for file access check
app.middleware("http")(file_access_middleware)

# Adding CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(files_router, prefix="/files", tags=["files"]) 