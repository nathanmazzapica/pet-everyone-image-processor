import json
import os
import uuid
from typing import Optional

from fastapi import Body, Depends, FastAPI, Header, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse

from src.api.models import StatusResponse, UploadRequest, UploadResponse

app = FastAPI(title="Pet Everyone Image Processor")


def get_shared_secret() -> str:
    shared_secret = os.getenv("PE_SHARED_SECRET")
    if not shared_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Shared secret not configured",
        )
    return shared_secret


def verify_shared_secret(
    x_pe_secret: Optional[str] = Header(default=None, alias="X-PE-Secret"),
    shared_secret: str = Depends(get_shared_secret),
) -> None:
    """
    Verifies if the provided shared secret matches the expected shared secret.

    This function checks the incoming `X-PE-Secret` header against a predefined shared
    secret. If the header value is missing or does not match, an HTTP 401 Unauthorized
    exception is raised.

    Parameters:
        x_pe_secret (Optional[str]): The value of the `X-PE-Secret` header, passed
            automatically by the header extraction mechanism. Defaults to None
            if not provided in the request.
        shared_secret (str): The expected shared secret. It is injected via dependency
            injection from the `get_shared_secret` function.

    Raises:
        HTTPException: Raised with status code 401 if the shared secret does not match
            or is missing.
    """
    if not x_pe_secret or x_pe_secret != shared_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )


@app.get("/ping")
def ping() -> dict:
    return {"status": "ok"}


@app.post("/upload", status_code=status.HTTP_201_CREATED, response_model=UploadResponse)
async def upload(
        file: UploadFile = File(...),
        x_pe_secret: Optional[str] = Header(default=None, alias="X-PE-Secret"),
        shared_secret: str = Depends(get_shared_secret),
) -> UploadResponse:
    if not x_pe_secret or x_pe_secret != shared_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )

    image_bytes = await file.read()




    image_id = str(uuid.uuid4())
    return UploadResponse(image_id=image_id, status="queued")
