import os
import sqlite3

import uvicorn
from dotenv import load_dotenv

from src.api.app import PetEveryoneImageProcessorAPI
from src.repository.job_repository import JobRepository
from src.repository.preprocess_job_repository import PreprocessJobRepository
from src.service.image_processing_service import ImageProcessingService
from src.storage.storage import LocalStorage


def run_app():
    print("Starting app")
    load_dotenv()
    secret = os.getenv("SECRET_KEY")
    if secret is None:
        raise Exception("SECRET_KEY is not set")
    conn = sqlite3.connect("jobs.db")
    repo = JobRepository(conn)
    prepo = PreprocessJobRepository(conn)
    storage = LocalStorage(base_path="storage")
    service = ImageProcessingService(storage, None, repo, prepo)
    api = PetEveryoneImageProcessorAPI(secret, service)
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(api.app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    run_app()