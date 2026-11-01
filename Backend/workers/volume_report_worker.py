"""RQ worker for volume-report jobs (own queue, so heavy parsing never blocks document ingestion).

Run with: python -m workers.volume_report_worker
"""

import logging

from redis import Redis
from rq import Worker

from app.core import model_registry  # noqa: F401 - registers all models on Base.metadata
from app.core.config import get_settings

settings = get_settings()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    worker = Worker([settings.vr_queue_name], connection=Redis.from_url(settings.redis_url))
    worker.work()


if __name__ == "__main__":
    main()
