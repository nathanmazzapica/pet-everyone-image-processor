import uuid
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, status, UploadFile, File

from src.security.virus_scanner import VirusScanner, VirusScannerError
from src.service.image_processing_service import ImageProcessingService
from src.api.models import UploadResponse


class PetEveryoneImageProcessorAPI:
    def __init__(
        self,
        shared_secret: str,
        image_processing_service: ImageProcessingService,
        virus_scanner: VirusScanner,
        title: str = "Pet Everyone Image Processor",
    ):
        self._shared_secret = shared_secret
        self._image_processing_service = image_processing_service
        self.virus_scanner = virus_scanner
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
            if file.size is not None and file.size > 25 * 1024 * 1024:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File size exceeds 25MB",
                )
            try:
                image_bytes = await file.read()

                try:
                    signature = self.virus_scanner.scan(image_bytes)
                    if signature is not None:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Virus detected: {signature}",
                        )
                except VirusScannerError as vse:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=f"Virus scanner error: {vse}",
                    )


                image_id = uuid.uuid4()
                self._image_processing_service.submit_upload(image_bytes, image_id)
                return UploadResponse(image_id=str(image_id), status="queued")
            finally:
                await file.close()
