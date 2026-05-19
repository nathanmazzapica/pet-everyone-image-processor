import uuid
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, status, UploadFile, File

from src.service.image_processing_service import ImageProcessingService
from src.api.models import UploadResponse


class PetEveryoneImageProcessorAPI:
    def __init__(
        self,
        shared_secret: str,
        image_processing_service: ImageProcessingService,
        title: str = "Pet Everyone Image Processor",
    ):
        self._shared_secret = shared_secret
        self._image_processing_service = image_processing_service
        self.app = FastAPI(title=title)
        self._register_routes()

    def _verify_shared_secret(
        self,
        x_pe_secret: Optional[str] = Header(default=None, alias="X-PE-Secret"),
    ) -> None:
        if not x_pe_secret or x_pe_secret != self._shared_secret:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized",
            )

    def _register_routes(self) -> None:
        @self.app.get("/ping")
        def ping() -> dict:
            return {"status": "ok"}

        @self.app.post("/upload", status_code=status.HTTP_201_CREATED, response_model=UploadResponse)
        async def upload(
            file: UploadFile = File(...),
            _: None = Depends(self._verify_shared_secret),
        ) -> UploadResponse:
            image_bytes = await file.read()

            image_id = uuid.uuid4()
            self._image_processing_service.submit_upload(image_bytes, image_id)
            return UploadResponse(image_id=str(image_id), status="queued")
