import uuid
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, status, UploadFile, File
from starlette.concurrency import run_in_threadpool

from src.service.exceptions import JobFailedError
from src.security.virus_scanner import VirusScanner
from src.security.exceptions import VirusScannerError
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
        self._virus_scanner = virus_scanner
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
            try:
                image_bytes = await file.read()
                if len(image_bytes) > ImageProcessingService.MAX_UPLOAD_SIZE:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"File size exceeds "
                            f"{ImageProcessingService.MAX_UPLOAD_SIZE // (1024 * 1024)}MB"
                        ),
                    )

                try:
                    signature = await run_in_threadpool(
                        self._virus_scanner.scan, image_bytes
                    )
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
                try:
                    self._image_processing_service.submit_upload(image_bytes, image_id)
                except JobFailedError as jfe:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Failed to process image: {jfe}",
                    ) from jfe

                return UploadResponse(image_id=str(image_id), status="queued")
            finally:
                await file.close()
