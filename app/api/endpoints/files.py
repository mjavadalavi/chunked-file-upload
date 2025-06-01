from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, Request, Header
from fastapi.responses import FileResponse
from app.core.security import get_current_user_id
from app.schemas.file import (
    InitSessionRequest, InitSessionResponse, InitSessionResponseData,
    ChunkUploadResponse, CompleteSessionRequest, CompleteSessionResponse, CompleteSessionResponseData
)
from app.services.file_service import file_service
from uuid import uuid4
from app.core.config import settings
import os
from app.core.session import session_map
from typing import Optional
import re

router = APIRouter()

@router.post("/", response_model=InitSessionResponse)
async def create_file(
    req: InitSessionRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    POST /files - Initialize a new file upload session
    """
    base_path = os.path.join(settings.LOCAL_TEMP_CHUNK_PATH, req.file_id)
    await file_service.save_chunk(req.file_id, -1, b"")  # Ensure dir exists (dummy chunk)
    if os.path.exists(os.path.join(base_path, "chunk_-1")):
        os.remove(os.path.join(base_path, "chunk_-1"))
    session_map[req.file_id] = {
        "user_id": user_id,
        "original_file_name": req.original_file_name
    }
    return InitSessionResponse(
        data=InitSessionResponseData(file_id=req.file_id)
    )

@router.get("/{file_id}")
async def get_file(
    file_id: int,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    GET /files/{file_id} - Download a file
    """
    user_file_dir = os.path.join(settings.PERSISTENT_LOCAL_STORAGE_PATH, "final", current_user_id, str(file_id))
    
    if not os.path.exists(user_file_dir):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
    
    files = [f for f in os.listdir(user_file_dir) if os.path.isfile(os.path.join(user_file_dir, f))]
    
    if not files:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
    
    file_path = os.path.join(user_file_dir, files[0])
    filename = files[0]
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/octet-stream'
    )

@router.get("/")
async def list_files(user_id: str = Depends(get_current_user_id)):
    """
    GET /files - List user's files
    """
    files = file_service.list_user_files(user_id)
    return {"status": "success", "files": files}

@router.put("/{file_id}", response_model=ChunkUploadResponse)
async def upload_chunk_to_file(
    file_id: str,
    chunk: UploadFile = File(...),
    chunk_index: Optional[int] = Form(None),
    content_range: Optional[str] = Header(None),
    user_id: str = Depends(get_current_user_id)
):
    """
    PUT /files/{file_id} - Upload a chunk to an existing file session
    chunk_index from form data OR Content-Range header format: "bytes start-end/total"
    """
    if not file_service.check_user_access(file_id, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found or access denied.")
    
    # If chunk_index is not provided, calculate it from Content-Range header
    if chunk_index is None:
        if content_range:
            # Parse Content-Range: bytes 0-1023/2048 => chunk_index based on chunk size
            match = re.match(r'bytes (\d+)-(\d+)/(\d+)', content_range)
            if match:
                start, end, total = map(int, match.groups())
                chunk_size = end - start + 1
                chunk_index = start // chunk_size
            else:
                chunk_index = 0
        else:
            raise HTTPException(status_code=400, detail="Either chunk_index or Content-Range header is required")
    
    chunk_data = await chunk.read()
    await file_service.save_chunk(file_id, chunk_index, chunk_data)
    return ChunkUploadResponse()

@router.patch("/{file_id}", response_model=CompleteSessionResponse)
async def complete_file_upload(
    file_id: str,
    req: CompleteSessionRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    PATCH /files/{file_id} - Complete the file upload process
    """
    if not file_service.check_user_access(file_id, user_id, req.main_service_file_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found or access denied.")
    
    session = session_map.get(file_id)
    merged_file_path = os.path.join(settings.PERSISTENT_LOCAL_STORAGE_PATH, file_id, "merged_final_file")
    
    try:
        await file_service.merge_chunks(file_id, req.total_chunks, merged_file_path)

        # Clean up logic
        if settings.STORAGE_BACKEND == "s3":
            s3_key = f"{user_id}/{req.main_service_file_id}/{session['original_file_name']}"
            file_path_or_key = await file_service.upload_file(merged_file_path, s3_key)
            await file_service.cleanup_session(file_id)  # Delete all chunks
            await file_service.delete_file(file_path_or_key)  # Delete merged file
            file_url = f"{settings.S3_ENDPOINT_URL}/{settings.S3_BUCKET_NAME}/{s3_key}"
            session_map.pop(file_id, None)
        else:
            await file_service.cleanup_session(file_id) # Only delete chunks, merged stays in final
            file_url = f"{settings.UPLOAD_SERVICE_BASE_URL}/files/{req.main_service_file_id}"
            
        return CompleteSessionResponse(
            status="success",
            message="File upload completed and main service notified.",
            data=CompleteSessionResponseData(file_download_url=file_url)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="File upload failed.")

@router.delete("/{file_id}")
async def delete_file(
    file_id: int,
    user_id: str = Depends(get_current_user_id)
):
    """
    DELETE /files/{file_id} - Delete a file
    """
    try:
        success = await file_service.delete_user_file(user_id, file_id)
        if success:
            return {"status": "success", "message": f"File {file_id} deleted successfully."}
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File {file_id} not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file {file_id}: {str(e)}")
