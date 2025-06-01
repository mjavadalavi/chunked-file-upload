from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import InvalidTokenError
from app.core.config import settings
from typing import Dict, Any
import re

security = HTTPBearer()


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.MAIN_SERVICE_JWT_PUBLIC_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.EXPECTED_JWT_AUDIENCE,
            issuer=settings.EXPECTED_JWT_ISSUER,
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token: missing sub.")
        return user_id
    except InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token validation error.")


def get_jwt_payload(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Returns the full JWT payload
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.MAIN_SERVICE_JWT_PUBLIC_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.EXPECTED_JWT_AUDIENCE,
            issuer=settings.EXPECTED_JWT_ISSUER,
        )
        return payload
    except InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token validation error.")


def check_file_access(payload: Dict[str, Any], file_id: int) -> bool:
    """
    Checks if the user has access to the requested file based on the file_id in the JWT payload
    """
    user_id = payload.get("sub")
    if not user_id:
        return False
    
    # JWT contains allowed file_id for this token
    allowed_file_id = payload.get("file_id")
    
    # Checking if the requested file_id matches the file_id in the JWT
    if allowed_file_id is None:
        return False
        
    # file_id must match exactly
    return int(allowed_file_id) == int(file_id)


async def file_access_middleware(request: Request, call_next):
    """
    Middleware for checking file access based on file_id in JWT
    """
    # List of routes that need file access check
    file_access_routes = [
        r'/upload/download/(\d+)', # Download file
        r'/upload/init',           # Start upload (file_id is in the body)
        r'/upload/complete',       # Complete upload (file_id is in the body)
        r'/upload/file'            # Delete file (file_id is in the body)
    ]
    
    path = request.url.path
    
    # Checking if this route needs file access check
    needs_file_check = False
    file_id_from_url = None
    
    for route_pattern in file_access_routes:
        match = re.match(route_pattern, path)
        if match:
            needs_file_check = True
            if match.groups():  # If file_id is in the URL
                file_id_from_url = int(match.group(1))
            break
    
    if needs_file_check:
        # Getting JWT from header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid authorization header")
        
        token = auth_header.split(" ")[1]
        
        try:
            # Decoding JWT
            payload = jwt.decode(
                token,
                settings.MAIN_SERVICE_JWT_PUBLIC_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                audience=settings.EXPECTED_JWT_AUDIENCE,
                issuer=settings.EXPECTED_JWT_ISSUER,
            )
            
            # Determining file_id to check
            requested_file_id = None
            
            # If file_id is in the URL
            if file_id_from_url is not None:
                requested_file_id = file_id_from_url
            
            # If file_id is in the body
            elif path in ['/upload/init', '/upload/complete', '/upload/file']:
                # Reading body
                body = await request.body()
                if body:
                    import json
                    try:
                        body_data = json.loads(body)
                        # For init and complete, use main_service_file_id
                        # For delete, use file_id
                        if path == '/upload/file':
                            requested_file_id = body_data.get('file_id')
                        else:
                            requested_file_id = body_data.get('main_service_file_id')
                    except json.JSONDecodeError:
                        pass
                
                # Rebuilding request with the same body so the endpoint can read it
                async def receive():
                    return {"type": "http.request", "body": body}
                request._receive = receive
            
            if requested_file_id is not None:
                if not check_file_access(payload, requested_file_id):
                    jwt_file_id = payload.get("file_id", "unknown")
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Access denied. JWT is for file {jwt_file_id}, but you requested file {requested_file_id}."
                    )
            else:
                # If we couldn't find file_id, be cautious
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Could not determine file_id from request."
                )
            
            # Adding JWT payload to request so endpoints can use it
            request.state.jwt_payload = payload
            
        except InvalidTokenError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token validation error")
    
    response = await call_next(request)
    return response 