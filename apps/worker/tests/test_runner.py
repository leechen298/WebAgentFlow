from app.jobs.runner import JobRunner


def test_job_runner_stores_poll_interval() -> None:
    runner = JobRunner(poll_interval=9)

    assert runner.poll_interval == 9


def test_run_forever_logs_startup_and_keyboard_interrupt(monkeypatch) -> None:
    runner = JobRunner(poll_interval=3)
    info_messages: list[tuple[str, tuple[object, ...]]] = []
    debug_messages: list[str] = []

    def fake_info(message: str, *args: object) -> None:
        info_messages.append((message, args))

    def fake_debug(message: str) -> None:
        debug_messages.append(message)

    def fake_sleep(_: int) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr("app.jobs.runner.logger.info", fake_info)
    monkeypatch.setattr("app.jobs.runner.logger.debug", fake_debug)
    monkeypatch.setattr("app.jobs.runner.time.sleep", fake_sleep)

    runner.run_forever()

    assert info_messages[0] == ("WebAgentFlow worker started", ())
    assert info_messages[1] == ("Worker poll interval: %s seconds", (3,))
    assert info_messages[2] == ("WebAgentFlow worker stopped", ())
    assert debug_messages == ["Worker heartbeat"]
