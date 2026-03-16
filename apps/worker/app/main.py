from app.core.config import settings
from app.core.logging import configure_logging
from app.jobs.runner import JobRunner


def main() -> None:
    configure_logging(settings.log_level)
    runner = JobRunner(poll_interval=settings.worker_poll_interval)
    runner.run_forever()


if __name__ == "__main__":
    main()
