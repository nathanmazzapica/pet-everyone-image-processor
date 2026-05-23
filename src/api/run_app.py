import argparse
import os
import sqlite3

import uvicorn
from dotenv import load_dotenv

from src.security.virus_scanner import VirusScanner
from src.api.app import PetEveryoneImageProcessorAPI
from src.repository.job_repository import JobRepository
from src.repository.preprocess_job_repository import PreprocessJobRepository
from src.service.image_processing_service import ImageProcessingService
from src.security.clamav_virus_scanner import ClamVirusScanner, VirusScannerError
from src.security.mock_virus_scanner import MockVirusScanner
from src.storage.storage import LocalStorage

parser = argparse.ArgumentParser()
parser.add_argument("--no-virus-scan", action="store_true")
args = parser.parse_args()

def run_app():
    print("Starting app")
    load_dotenv()
    secret = os.getenv("PE_SHARED_SECRET")
    if secret is None:
        raise Exception("PE_SHARED_SECRET is not set")
    conn = sqlite3.connect("jobs.db")
    repo = JobRepository(conn)
    prepo = PreprocessJobRepository(conn)
    storage = LocalStorage(base_path="storage")
    service = ImageProcessingService(storage, None, repo, prepo)
    scanner = _initialize_virus_scanner()
    api = PetEveryoneImageProcessorAPI(secret, service, scanner)
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(api.app, host="0.0.0.0", port=port)

def _initialize_virus_scanner() -> VirusScanner:
    print("Initializing virus scanner")
    mock = args.no_virus_scan
    if mock:
        return MockVirusScanner()
    try :
        sock = os.getenv("CLAMD_PATH", "/tmp/clamd.sock")
        return ClamVirusScanner(sock)
    except VirusScannerError as vse:
        print(f"[FATAL] Failed to initialize virus scanner: {vse}")
        raise



if __name__ == "__main__":
    run_app()