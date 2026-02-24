import sqlite3

from src.repository.repository import JobRepository


def create_repository(db_path: str) -> JobRepository:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return JobRepository(conn)


if __name__ == "__main__":
    repository = create_repository("jobs.db")
    _ = repository
