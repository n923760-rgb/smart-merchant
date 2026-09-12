import logging
import time

import redis

from app.core.config import get_settings
from app.core.logging import configure_logging

configure_logging(get_settings().log_level)
logger = logging.getLogger(__name__)


def main():
    client = redis.Redis.from_url(get_settings().redis_url)
    while True:
        client.ping()
        logger.info("worker heartbeat")
        time.sleep(30)


if __name__ == "__main__":
    main()
