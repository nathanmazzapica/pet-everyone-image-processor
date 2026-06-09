from typing import Optional

from pydantic import BaseModel


class UploadRequest(BaseModel):
    pet_id: str
    user_id: str
    secret: Optional[str] = None


class UploadResponse(BaseModel):
    pet_id: str
    status: str


class StatusResponse(BaseModel):
    pet_id: str
    status: str
