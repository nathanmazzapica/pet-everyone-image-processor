import os
import sqlite3

from dotenv import load_dotenv

from src.api.app import PetEveryoneImageProcessorAPI
from src.repository.repository import JobRepository
from src.service.image_processing_service import ImageProcessingService
from src.storage.storage import LocalStorage


def run_app():
    print("Starting app")
    conn = sqlite3.connect("jobs.db")
    repo = JobRepository(conn)
    storage = LocalStorage(base_path="storage")
    service = ImageProcessingService(storage, None, repo)
    load_dotenv()
    secret = os.getenv("SECRET_KEY")
    if secret is None:
        raise Exception("SECRET_KEY is not set")
    app = PetEveryoneImageProcessorAPI(secret, service)

if __name__ == "__main__":
    run_app()