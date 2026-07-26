import argparse
import logging
import multiprocessing
import os
import sqlite3
import time

from src.messaging.exceptions import PublisherError
from src.messaging.redis_publisher import RedisPublisher
from src.repository.exceptions import FatalDatabaseError
from src.repository.repository import Repository
from src.service.background_removal_service import BackgroundRemovalService
from src.service.exceptions import FatalServiceError
from src.service.preprocess_service import PreprocessService
from src.service.processors.background_remover import BackgroundRemover
from src.storage.storage import LocalStorage
from src.workers.background_removal_worker import Worker as BackgroundRemovalWorker
from src.workers.outbox_worker import OutboxWorker
from src.workers.preprocess_worker import Worker as PreprocessWorker

logger = logging.getLogger(__name__)


def _run_preprocess_worker():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [PID %(process)d] %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("pyvips").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)
    conn = sqlite3.connect("jobs.db")
    repo = Repository(conn)
    storage = LocalStorage(base_path="storage")
    service = PreprocessService(storage)
    worker = PreprocessWorker(repo, service)
    try:
        worker.run()
    except (FatalServiceError, FatalDatabaseError) as e:
        logger.exception("Fatal error in preprocess worker")
        conn.close()
        raise SystemExit(getattr(e, "status_code", 99)) from e
    except KeyboardInterrupt:
        conn.close()


def _run_bg_removal_worker():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [PID %(process)d] %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("pyvips").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)
    conn = sqlite3.connect("jobs.db")
    repo = Repository(conn)
    storage = LocalStorage(base_path="storage")
    logger.info("Loading background remover model")
    remover = BackgroundRemover()
    logger.info("Background remover model loaded")
    service = BackgroundRemovalService(storage, remover)
    worker = BackgroundRemovalWorker(repo, service)
    try:
        worker.run()
    except (FatalServiceError, FatalDatabaseError) as e:
        logger.exception("Fatal error in background removal worker")
        conn.close()
        raise SystemExit(getattr(e, "status_code", 99)) from e
    except KeyboardInterrupt:
        conn.close()


def _run_outbox_worker():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [PID %(process)d] %(levelname)s %(name)s: %(message)s",
    )
    conn = sqlite3.connect("jobs.db")
    repo = Repository(conn)
    publisher = RedisPublisher(os.getenv("REDIS_URL", "redis://localhost:6379"))
    worker = OutboxWorker(publisher, repo)
    try:
        worker.run()
    except (PublisherError, FatalDatabaseError) as e:
        logger.exception("Fatal error in outbox worker")
        conn.close()
        raise SystemExit(getattr(e, "status_code", 99)) from e
    except KeyboardInterrupt:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pet Everyone Image Processor")
    parser.add_argument(
        "--preprocess-workers",
        type=int,
        default=1,
        help="Number of preprocess worker processes to start (default: 1)",
    )
    parser.add_argument(
        "--bg-removal-workers",
        type=int,
        default=1,
        help="Number of background removal worker processes to start (default: 1)",
    )
    parser.add_argument(
        "--outbox-workers",
        type=int,
        default=1,
        help="Number of outbox worker processes to start (default: 1)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [PID %(process)d] %(levelname)s %(name)s: %(message)s",
    )

    preprocess_worker_procs = []
    for _ in range(args.preprocess_workers):
        p = multiprocessing.Process(target=_run_preprocess_worker, daemon=True)
        p.start()
        logger.info("Started preprocess worker PID %d", p.pid)
        preprocess_worker_procs.append(p)

    bg_removal_worker_procs = []
    for _ in range(args.bg_removal_workers):
        p = multiprocessing.Process(target=_run_bg_removal_worker, daemon=True)
        p.start()
        logger.info("Started background removal worker PID %d", p.pid)
        bg_removal_worker_procs.append(p)

    outbox_worker_procs = []
    for _ in range(args.outbox_workers):
        p = multiprocessing.Process(target=_run_outbox_worker, daemon=True)
        p.start()
        logger.info("Started outbox worker PID %d", p.pid)
        outbox_worker_procs.append(p)

    conn = sqlite3.connect("jobs.db")
    repo = Repository(conn)
    tick = 0
    try:
        while True:
            for p in preprocess_worker_procs:
                if not p.is_alive():
                    code = p.exitcode if p.exitcode is not None else 99
                    logger.error(
                        "Preprocess worker died. Exit code: %s desc: %s",
                        code,
                        repo.get_error_desc(code),
                    )
                    raise SystemExit(code)
            for p in bg_removal_worker_procs:
                if not p.is_alive():
                    code = p.exitcode if p.exitcode is not None else 99
                    logger.error(
                        "Background-removal worker died. Exit code: %s desc: %s",
                        code,
                        repo.get_error_desc(code),
                    )
                    raise SystemExit(code)
            for p in outbox_worker_procs:
                if not p.is_alive():
                    code = p.exitcode if p.exitcode is not None else 99
                    logger.error(
                        "Outbox worker died. Exit code: %s desc: %s",
                        code,
                        repo.get_error_desc(code),
                    )
                    raise SystemExit(code)
            if tick % 60 == 0:
                repo.unlock_stale_jobs()

            tick += 1
            time.sleep(5)
    except KeyboardInterrupt:
        logger.info("Shutting down")
    finally:
        for p in preprocess_worker_procs + bg_removal_worker_procs + outbox_worker_procs:
            p.terminate()
            p.join()
        conn.close()
