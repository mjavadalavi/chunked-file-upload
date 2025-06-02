import logging
from fastapi import FastAPI, Request, Response
from app.api.endpoints.files import router as files_router
from app.core.config import settings
from app.core.security import file_access_middleware
from fastapi.middleware.cors import CORSMiddleware

# تنظیم logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Hayula Upload Service",
    version="1.0.0",
    openapi_url=None if settings.ENV == "production" else f"/openapi.json",
    docs_url=None if settings.ENV == "production" else f"/docs",
    redoc_url=None if settings.ENV == "production" else f"/redoc"
)

# CORS Debug Middleware
@app.middleware("http")
async def cors_debug_middleware(request: Request, call_next):
    origin = request.headers.get("origin")
    if origin:
        logging.info(f"Request from origin: {origin}")
    
    response = await call_next(request)
    
    # اضافه کردن CORS headers به صورت manual
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Accept, Accept-Language, Content-Language, Content-Type, Authorization, X-Requested-With, Origin, Access-Control-Request-Method, Access-Control-Request-Headers, Content-Range, X-File-Name, X-File-Size, X-Chunk-Index"
        response.headers["Access-Control-Expose-Headers"] = "Content-Length, Content-Range, Accept-Ranges"
    
    return response

# Adding middleware for file access check
app.middleware("http")(file_access_middleware)

# Adding CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://dev-upload.hyul.ir",
        "https://upload.hyul.ir", 
        "https://dev.hayula.monster",
        "https://hayula.monster",
        "*"  # fallback
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=[
        "Accept",
        "Content-Type",
        "Origin",
        "Authorization",
        "Content-Range",
        "X-Requested-With",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers"
    ],
)

app.include_router(files_router, prefix="/files", tags=["files"]) 