from fastapi import FastAPI
from app.api.endpoints.upload import router as upload_router

app = FastAPI(title="Hayula Upload Service")

app.include_router(upload_router, prefix="/upload", tags=["upload"]) 