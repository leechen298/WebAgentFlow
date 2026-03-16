import logging
import time

logger = logging.getLogger(__name__)


class JobRunner:
    def __init__(self, poll_interval: int = 5) -> None:
        self.poll_interval = poll_interval

    def run_forever(self) -> None:
        logger.info("WebAgentFlow worker started")
        logger.info("Worker poll interval: %s seconds", self.poll_interval)

        try:
            while True:
                logger.debug("Worker heartbeat")
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            logger.info("WebAgentFlow worker stopped")
