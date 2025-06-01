from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, Body
from fastapi.responses import FileResponse
from app.core.security import get_current_user_id
from app.schemas.upload import (
    InitSessionRequest, InitSessionResponse, InitSessionResponseData,
    ChunkUploadResponse, CompleteSessionRequest, CompleteSessionResponse, CompleteSessionResponseData
)
from app.services.file_service import file_service
from uuid import uuid4
from app.core.config import settings
import os
from app.core.session import session_map

router = APIRouter()

@router.post("/init", response_model=InitSessionResponse)
async def init_session(
    req: InitSessionRequest,
    user_id: str = Depends(get_current_user_id)
):
    upload_session_id = str(uuid4())
    base_path = os.path.join(settings.LOCAL_TEMP_CHUNK_PATH, upload_session_id)
    await file_service.save_chunk(upload_session_id, -1, b"")  # Ensure dir exists (dummy chunk)
    if os.path.exists(os.path.join(base_path, "chunk_-1")):
        os.remove(os.path.join(base_path, "chunk_-1"))
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
    session = session_map.get(upload_session_id)
    if not file_service.check_user_access(upload_session_id, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid upload_session_id.")
    chunk_data = await chunk.read()
    await file_service.save_chunk(upload_session_id, chunk_index, chunk_data)
    return ChunkUploadResponse()

@router.post("/complete", response_model=CompleteSessionResponse)
async def complete_session(
    req: CompleteSessionRequest,
    user_id: str = Depends(get_current_user_id)
):
    if not file_service.check_user_access(req.upload_session_id, user_id, req.main_service_file_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid upload_session_id or file_id.")
    session = session_map.get(req.upload_session_id)
    merged_file_path = os.path.join(settings.PERSISTENT_LOCAL_STORAGE_PATH, req.upload_session_id, "merged_final_file")
    try:
        await file_service.merge_chunks(req.upload_session_id, req.total_chunks, merged_file_path)
        s3_key = f"{user_id}/{req.main_service_file_id}/{session['original_file_name']}"
        file_path_or_key = await file_service.upload_file(merged_file_path, s3_key)
        # Clean up logic
        if settings.STORAGE_BACKEND == "s3":
            await file_service.cleanup_session(req.upload_session_id)  # Delete all chunks
            await file_service.delete_file(merged_file_path)  # Delete merged file
            file_url = f"{settings.S3_ENDPOINT_URL}/{settings.S3_BUCKET_NAME}/{s3_key}"
            session_map.pop(req.upload_session_id, None)
        else:
            await file_service.cleanup_session(req.upload_session_id)  # Only delete chunks, merged stays in final
            # برای local storage، یک URL دانلود پذیر برمی‌گردونیم
            file_url = f"{settings.UPLOAD_SERVICE_BASE_URL}/upload/download/{req.main_service_file_id}"
        return CompleteSessionResponse(
            status="success",
            message="File upload completed and main service notified.",
            data=CompleteSessionResponseData(file_download_url=file_url)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="File upload failed.")

@router.get("/download/{file_id}")
async def download_file(
    file_id: int,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    دانلود فایل از local storage
    فقط کاربر صاحب فایل می‌تونه دانلود کنه
    """

    # پیدا کردن فایل در local storage
    user_file_dir = os.path.join(settings.PERSISTENT_LOCAL_STORAGE_PATH, "final", current_user_id, str(file_id))
    
    if not os.path.exists(user_file_dir):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
    
    # پیدا کردن اولین فایل در دایرکتوری (باید فقط یک فایل باشه)
    files = [f for f in os.listdir(user_file_dir) if os.path.isfile(os.path.join(user_file_dir, f))]
    
    if not files:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
    
    file_path = os.path.join(user_file_dir, files[0])
    filename = files[0]
    
    # برگرداندن فایل برای دانلود
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/octet-stream'
    )

@router.delete("/file")
async def delete_file(
    upload_session_id: str = Body(None, embed=True),
    user_id: str = Depends(get_current_user_id)
):
    if upload_session_id:
        if not file_service.check_user_access(upload_session_id, user_id):
            return {"status": "error", "message": "Access denied."}
        await file_service.cleanup_session(upload_session_id)
        return {"status": "success", "message": "Session folder and related files deleted (if existed)."}
    else:
        return {"status": "error", "message": "You must provide upload_session_id."}

@router.get("/files")
async def list_user_files(user_id: str = Depends(get_current_user_id)):
    files = file_service.list_user_files(user_id)
    return {"status": "success", "files": files} 