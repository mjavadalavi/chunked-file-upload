from pydantic import BaseModel, Field
from typing import Optional

class InitSessionRequest(BaseModel):
    file_id: int
    original_file_name: str

class InitSessionResponseData(BaseModel):
    file_id: str

class InitSessionResponse(BaseModel):
    status: str = "success"
    message: str = "File created successfully."
    data: InitSessionResponseData

class ChunkUploadResponse(BaseModel):
    status: str = "success"
    message: str = "Chunk uploaded successfully."

class CompleteSessionRequest(BaseModel):
    total_chunks: int
    main_service_file_id: int

class CompleteSessionResponseData(BaseModel):
    file_download_url: str

class CompleteSessionResponse(BaseModel):
    status: str = "success"
    message: str = "File upload completed and main service notified."
    data: CompleteSessionResponseData 