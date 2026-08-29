"""RQ worker process that runs the document ingestion pipeline.

Run with: python -m workers.ingestion_worker
"""

from redis import Redis
from rq import Worker

from app.core import model_registry  # noqa: F401 - registers all models on Base.metadata
from app.core.config import get_settings

settings = get_settings()


def main() -> None:
    connection = Redis.from_url(settings.redis_url)
    worker = Worker([settings.ingestion_queue_name], connection=connection)
    worker.work()


if __name__ == "__main__":
    main()
