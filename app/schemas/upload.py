from pydantic import BaseModel, Field
from typing import Optional

class InitSessionRequest(BaseModel):
    main_service_file_id: int
    original_file_name: str

class InitSessionResponseData(BaseModel):
    upload_session_id: str

class InitSessionResponse(BaseModel):
    status: str = "success"
    message: str = "Upload session initialized."
    data: InitSessionResponseData

class ChunkUploadResponse(BaseModel):
    status: str = "success"
    message: str = "Chunk uploaded successfully."

class CompleteSessionRequest(BaseModel):
    upload_session_id: str
    total_chunks: int
    main_service_file_id: int

class CompleteSessionResponseData(BaseModel):
    file_path_on_upload_service: str

class CompleteSessionResponse(BaseModel):
    status: str = "success"
    message: str = "File upload completed and main service notified."
    data: CompleteSessionResponseData 