# Chunked File Upload Microservice

This project is a chunked audio file upload microservice built with Python and FastAPI, supporting secure storage of files in both S3-compatible services and local storage.

## Features
- Receive audio files in chunked (multipart) form from clients
- JWT (RS256) authentication for security and access control
- Dual storage backend support: S3-compatible services (AWS S3) or local storage
- User-based access control and file isolation (files organized by user_id/file_id)
- Smart cleanup logic: different cleanup strategies for S3 vs local storage
- Automatic cleanup of temporary files after successful upload
- Async and non-blocking implementation for high scalability
- Docker support for easy deployment
- Factory pattern for storage backends

## Prerequisites
- Python 3.8+
- Docker (optional, for containerized deployment)
- Access to S3-Compatible service (optional, if using S3 backend)

## Installation & Setup

### Local Development
1. Clone the repository and navigate to the project directory.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file based on `.env.example` and set your configuration values.
4. Run with Uvicorn:
   ```bash
   uvicorn app.main:app --reload
   ```

### Docker Deployment
1. Build the Docker image:
   ```bash
   docker build -t upload-service .
   ```
2. Run the container:
   ```bash
   docker run --rm -p 8000:8000 upload-service
   ```

## Environment Variables

### Required Variables
- `MAIN_SERVICE_JWT_PUBLIC_KEY`: JWT public key for token validation
- `JWT_ALGORITHM`: Algorithm (usually RS256)
- `EXPECTED_JWT_ISSUER`: Valid token issuer (e.g., "hayula_main_service")
- `EXPECTED_JWT_AUDIENCE`: Valid token audience (e.g., "hayula_upload_service")

### Storage Configuration
- `STORAGE_BACKEND`: Storage backend type ("s3" or "local")
- `LOCAL_TEMP_CHUNK_PATH`: Path for temporary chunk storage (default: "/tmp/hayula_chunks")

### S3 Configuration (Required only if STORAGE_BACKEND=s3)
- `S3_ACCESS_KEY`: S3 access key
- `S3_SECRET_KEY`: S3 secret key
- `S3_BUCKET_NAME`: S3 bucket name
- `S3_ENDPOINT_URL`: S3 endpoint URL
- `S3_REGION_NAME`: S3 region name (optional)

### Example .env for Local Storage
```env
STORAGE_BACKEND=local
LOCAL_TEMP_CHUNK_PATH=/tmp/hayula_chunks
MAIN_SERVICE_JWT_PUBLIC_KEY=your_jwt_public_key
JWT_ALGORITHM=RS256
EXPECTED_JWT_ISSUER=hayula_main_service
EXPECTED_JWT_AUDIENCE=hayula_upload_service
```

### Example .env for S3 Storage
```env
STORAGE_BACKEND=s3
LOCAL_TEMP_CHUNK_PATH=/tmp/hayula_chunks
S3_ACCESS_KEY=your_s3_access_key
S3_SECRET_KEY=your_s3_secret_key
S3_BUCKET_NAME=your_bucket_name
S3_ENDPOINT_URL=url
S3_REGION_NAME=ir
MAIN_SERVICE_JWT_PUBLIC_KEY=your_jwt_public_key
JWT_ALGORITHM=RS256
EXPECTED_JWT_ISSUER=hayula_main_service
EXPECTED_JWT_AUDIENCE=hayula_upload_service
```

## API Documentation

All endpoints require JWT authentication via `Authorization: Bearer <token>` header.

### 1. Initialize Upload Session
`POST /upload/init`

**Headers:**
- `Authorization: Bearer <jwt_token>`

**Body:**
```json
{
  "main_service_file_id": 123,
  "original_file_name": "audio.mp3"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Upload session initialized.",
  "data": { "upload_session_id": "uuid-string" }
}
```

### 2. Upload Chunk
`POST /upload/chunk`

**Headers:**
- `Authorization: Bearer <jwt_token>`

**Form Data:**
- `upload_session_id`: Session ID from init endpoint
- `chunk_index`: Chunk number (starting from 0)
- `chunk`: Chunk file data

**Response:**
```json
{
  "status": "success",
  "message": "Chunk uploaded successfully."
}
```

### 3. Complete Upload
`POST /upload/complete`

**Headers:**
- `Authorization: Bearer <jwt_token>`

**Body:**
```json
{
  "upload_session_id": "uuid-string",
  "total_chunks": 10,
  "main_service_file_id": 123
}
```

**Response:**
```json
{
  "status": "success",
  "message": "File upload completed and main service notified.",
  "data": {
    "file_path_on_upload_service": "<file_url_or_path>"
  }
}
```

### 4. Delete Files
`DELETE /upload/file`

**Headers:**
- `Authorization: Bearer <jwt_token>`

**Body:**
```json
{
  "upload_session_id": "uuid-string"
}
```

### 5. List User Files
`GET /upload/files`

**Headers:**
- `Authorization: Bearer <jwt_token>`

**Response:**
```json
{
  "status": "success",
  "files": ["file1_url", "file2_url", ...]
}
```

## Storage Behavior

### S3 Storage
- Chunks are temporarily stored locally during upload
- Final file is uploaded to S3 with path: `{user_id}/{file_id}/{filename}`
- After successful S3 upload, all local temporary files are deleted
- File listing returns S3 URLs

### Local Storage
- Chunks are temporarily stored during upload
- Final file is moved to: `{LOCAL_TEMP_CHUNK_PATH}/final/{user_id}/{file_id}/{filename}`
- After successful merge, only chunks are deleted (final file remains)
- File listing returns local file paths

## Security Features
- User-based access control: users can only access their own files
- JWT token validation with RS256 algorithm
- File path isolation by user_id to prevent unauthorized access
- Input validation on all endpoints
- Secure file handling and cleanup

## Architecture
- **Factory Pattern**: Pluggable storage backends (S3 vs Local)
- **Service Layer**: FileService encapsulates all file operations
- **Session Management**: Centralized session handling to avoid circular imports
- **Async Operations**: Non-blocking file operations for better performance

## Development & Contribution
Pull requests and suggestions are welcome! Make sure to:
- Follow the existing code structure
- Add tests for new features
- Update documentation for any API changes
- Ensure Docker compatibility 
