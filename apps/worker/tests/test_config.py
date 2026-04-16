from app.core.config import settings


def test_default_worker_env() -> None:
    assert settings.worker_env in {"development", "staging", "production"}
    assert settings.log_level
    assert settings.worker_poll_interval > 0
