import json
import os
import uuid
from typing import Optional

from fastapi import Body, Depends, FastAPI, Header, HTTPException, status
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
    if not x_pe_secret or x_pe_secret != shared_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )


@app.get("/ping")
def ping() -> dict:
    return {"status": "ok"}


@app.post("/upload", status_code=status.HTTP_201_CREATED, response_model=UploadResponse)
def upload(
    payload: UploadRequest = Body(...),
    x_pe_secret: Optional[str] = Header(default=None, alias="X-PE-Secret"),
    shared_secret: str = Depends(get_shared_secret),
) -> UploadResponse:
    secret = x_pe_secret or payload.secret
    if not secret or secret != shared_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )

    image_id = str(uuid.uuid4())
    return UploadResponse(image_id=image_id, status="queued")


@app.get("/status/{image_id}", response_model=StatusResponse, dependencies=[Depends(verify_shared_secret)])
def status_check(image_id: str) -> StatusResponse:
    return StatusResponse(image_id=image_id, status="processing")


@app.get("/subscribe/{image_id}", dependencies=[Depends(verify_shared_secret)])
def subscribe(image_id: str) -> StreamingResponse:
    def event_stream():
        payload = json.dumps({"image_id": image_id, "status": "processing"})
        yield f"event: status\ndata: {payload}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
