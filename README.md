# Chunked File Upload Microservice

This project is a chunked audio file upload microservice built with Python and FastAPI, supporting secure storage of files in S3.

## Features
- Receive audio files in chunked (multipart) form
- JWT (RS256) authentication for security and access control
- Final file storage in S3 (compatible with any S3-Compatible service)
- Automatic cleanup of temporary files after successful upload
- Async and non-blocking implementation for high scalability

## Prerequisites
- Python 3.8+
- Access to S3-Compatible service

## Installation & Setup
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

## Important Environment Variables
- `MAIN_SERVICE_JWT_PUBLIC_KEY`: JWT public key
- `JWT_ALGORITHM`: Algorithm (usually RS256)
- `EXPECTED_JWT_ISSUER`: Valid token issuer
- `EXPECTED_JWT_AUDIENCE`: Valid token audience
- `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET_NAME`, `S3_ENDPOINT_URL`: S3 connection info
- `LOCAL_TEMP_CHUNK_PATH`: Path for temporary chunk storage

## API Documentation
### 1. Initialize Upload Session
`POST /upload/init`

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
  "data": { "upload_session_id": "..." }
}
```

### 2. Upload Chunk
`POST /upload/chunk`

**Form Data:**
- `upload_session_id`: Session ID
- `chunk_index`: Chunk number (starting from 0)
- `chunk`: Chunk file

**Response:**
```json
{
  "status": "success",
  "message": "Chunk uploaded successfully."
}
```

### 3. Complete Upload
`POST /upload/complete`

**Body:**
```json
{
  "upload_session_id": "...",
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
    "file_path_on_upload_service": "<s3_url_of_the_uploaded_file>"
  }
}
```

## Security Notes
- Only set JWT and S3 keys via environment variables.
- Always use HTTPS.
- Validate all inputs.

## Development & Contribution
Pull requests and suggestions are welcome! 