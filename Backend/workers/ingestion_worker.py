"""RQ worker process that runs the document ingestion pipeline.

Run with: python -m workers.ingestion_worker
"""

import logging

from redis import Redis
from rq import Worker

from app.core import model_registry  # noqa: F401 - registers all models on Base.metadata
from app.core.config import get_settings

settings = get_settings()


def main() -> None:
    # rq only configures its own loggers; without this the pipeline's INFO logs (step timings, OCR) are dropped.
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    connection = Redis.from_url(settings.redis_url)
    worker = Worker([settings.ingestion_queue_name], connection=connection)
    worker.work()


if __name__ == "__main__":
    main()
