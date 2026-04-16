from app import main as main_module


def test_main_configures_logging_and_runs_job_runner(monkeypatch) -> None:
    calls: dict[str, object] = {}

    class FakeRunner:
        def __init__(self, poll_interval: int) -> None:
            calls["poll_interval"] = poll_interval

        def run_forever(self) -> None:
            calls["ran"] = True

    monkeypatch.setattr(main_module, "configure_logging", lambda level: calls.setdefault("log_level", level))
    monkeypatch.setattr(main_module, "JobRunner", FakeRunner)

    main_module.main()

    assert calls == {
        "log_level": main_module.settings.log_level,
        "poll_interval": main_module.settings.worker_poll_interval,
        "ran": True,
    }
