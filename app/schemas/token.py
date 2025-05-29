from pydantic import BaseModel
from typing import Any

class TokenData(BaseModel):
    sub: str
    iss: str
    aud: str
    exp: int
    # You can add more fields if needed 