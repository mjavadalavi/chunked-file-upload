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
    کل JWT payload رو برمی‌گردونه تا بتونیم مجوزهای دسترسی رو بررسی کنیم
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
    بررسی می‌کنه که آیا کاربر به فایل مورد نظر دسترسی داره یا نه
    بر اساس file_id موجود در JWT payload
    """
    user_id = payload.get("sub")
    if not user_id:
        return False
    
    # JWT شامل file_id مجاز برای این توکن هست
    allowed_file_id = payload.get("file_id")
    
    # بررسی اینکه file_id درخواستی با file_id موجود در JWT مطابقت داره
    if allowed_file_id is None:
        return False
        
    # file_id باید دقیقاً مطابقت داشته باشه
    return int(allowed_file_id) == int(file_id)


async def file_access_middleware(request: Request, call_next):
    """
    Middleware برای بررسی دسترسی فایل بر اساس file_id موجود در JWT
    """
    # لیست route هایی که نیاز به بررسی دسترسی فایل دارن
    file_access_routes = [
        r'/upload/download/(\d+)',  # دانلود فایل
        r'/upload/init',           # شروع آپلود (file_id توی body هست)
        r'/upload/complete'        # تکمیل آپلود (file_id توی body هست)
    ]
    
    path = request.url.path
    
    # بررسی اینکه آیا این route نیاز به بررسی دسترسی فایل داره
    needs_file_check = False
    file_id_from_url = None
    
    for route_pattern in file_access_routes:
        match = re.match(route_pattern, path)
        if match:
            needs_file_check = True
            if match.groups():  # اگر file_id توی URL هست
                file_id_from_url = int(match.group(1))
            break
    
    if needs_file_check:
        # گرفتن JWT از header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid authorization header")
        
        token = auth_header.split(" ")[1]
        
        try:
            # Decode کردن JWT
            payload = jwt.decode(
                token,
                settings.MAIN_SERVICE_JWT_PUBLIC_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                audience=settings.EXPECTED_JWT_AUDIENCE,
                issuer=settings.EXPECTED_JWT_ISSUER,
            )
            
            # مشخص کردن file_id که باید بررسی بشه
            requested_file_id = None
            
            # اگر file_id توی URL هست
            if file_id_from_url is not None:
                requested_file_id = file_id_from_url
            
            # اگر file_id توی body هست
            elif path in ['/upload/init', '/upload/complete']:
                # خواندن body
                body = await request.body()
                if body:
                    import json
                    try:
                        body_data = json.loads(body)
                        requested_file_id = body_data.get('main_service_file_id')
                    except json.JSONDecodeError:
                        pass
                
                # بازسازی request با همان body تا endpoint بتونه بخونه
                async def receive():
                    return {"type": "http.request", "body": body}
                request._receive = receive
            
            # بررسی دسترسی به file_id درخواستی
            if requested_file_id is not None:
                if not check_file_access(payload, requested_file_id):
                    jwt_file_id = payload.get("file_id", "unknown")
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Access denied. JWT is for file {jwt_file_id}, but you requested file {requested_file_id}."
                    )
            else:
                # اگر نتونستیم file_id رو پیدا کنیم، احتیاط می‌کنیم
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Could not determine file_id from request."
                )
            
            # JWT payload رو به request اضافه می‌کنیم تا endpoint ها بتونن استفاده کنن
            request.state.jwt_payload = payload
            
        except InvalidTokenError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token validation error")
    
    response = await call_next(request)
    return response 