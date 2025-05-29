from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from app.core.security import get_current_user_id
from app.schemas.upload import (
    InitSessionRequest, InitSessionResponse, InitSessionResponseData,
    ChunkUploadResponse, CompleteSessionRequest, CompleteSessionResponse, CompleteSessionResponseData
)
from app.services import storage
from uuid import uuid4
import os
import asyncio

router = APIRouter()

# In-memory session mapping (replace with Redis/db in production)
session_map = {}

@router.post("/init", response_model=InitSessionResponse)
async def init_session(
    req: InitSessionRequest,
    user_id: str = Depends(get_current_user_id)
):
    upload_session_id = str(uuid4())
    # Create temp dir for chunks
    base_path = os.path.join(storage.settings.LOCAL_TEMP_CHUNK_PATH, upload_session_id)
    os.makedirs(base_path, exist_ok=True)
    # Save session mapping
    session_map[upload_session_id] = {
        "user_id": user_id,
        "main_service_file_id": req.main_service_file_id,
        "original_file_name": req.original_file_name
    }
    return InitSessionResponse(
        data=InitSessionResponseData(upload_session_id=upload_session_id)
    )

@router.post("/chunk", response_model=ChunkUploadResponse)
async def upload_chunk(
    upload_session_id: str = Form(...),
    chunk_index: int = Form(...),
    chunk: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id)
):
    # Validate session
    session = session_map.get(upload_session_id)
    if not session or session["user_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid upload_session_id.")
    # Save chunk
    chunk_data = await chunk.read()
    await asyncio.to_thread(storage.save_chunk_locally, upload_session_id, chunk_index, chunk_data)
    return ChunkUploadResponse()

@router.post("/complete", response_model=CompleteSessionResponse)
async def complete_session(
    req: CompleteSessionRequest,
    user_id: str = Depends(get_current_user_id)
):
    session = session_map.get(req.upload_session_id)
    if not session or session["user_id"] != user_id or session["main_service_file_id"] != req.main_service_file_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid upload_session_id or file_id.")

    merged_file_path = os.path.join(storage.settings.LOCAL_TEMP_CHUNK_PATH, req.upload_session_id, "merged_final_file")
    try:
        await asyncio.to_thread(storage.merge_chunks, req.upload_session_id, req.total_chunks, merged_file_path)
        s3_key = f"{user_id}/{req.main_service_file_id}/{session['original_file_name']}"
        await asyncio.to_thread(storage.upload_file_to_s3, merged_file_path, s3_key)
        await asyncio.to_thread(storage.cleanup_local_session, req.upload_session_id)
        await asyncio.to_thread(storage.cleanup_file, merged_file_path)
        session_map.pop(req.upload_session_id, None)
        s3_url = f"{storage.settings.S3_ENDPOINT_URL}/{storage.settings.S3_BUCKET_NAME}/{s3_key}"
        return CompleteSessionResponse(
            status="success",
            message="File upload completed and main service notified.",
            data=CompleteSessionResponseData(file_path_on_upload_service=s3_url)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="File upload failed.") 