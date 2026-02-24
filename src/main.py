import argparse
import os
import sys
import sqlite3

from src.repository.repository import JobRepository
from src.service import background_remover
from src.storage.storage import LocalStorage


def create_repository(db_path: str) -> JobRepository:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return JobRepository(conn)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pet Everyone Image Processor")
    parser.add_argument(
        "--storage",
        choices=["local", "s3"],
        default="local",
        help="Storage backend to use (default: local)",
    )
    args = parser.parse_args()

    try:
        repository = create_repository("jobs.db")
    except Exception as exc:
        print(f"[FATAL] {exc}")
        sys.exit(1)

    if args.storage == "s3":
        print("[FATAL] S3 storage is not implemented yet.")
        sys.exit(1)

    base_path = os.getenv("LOCAL_BASE_PATH", ".")
    storage = LocalStorage(base_path)
    _ = repository
    bg_service = background_remover.BackgroundRemover(repository, storage)
