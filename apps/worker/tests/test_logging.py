from app.core import logging as logging_module


def test_configure_logging_builds_expected_dict_config(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_dict_config(config: dict[str, object]) -> None:
        captured.update(config)

    monkeypatch.setattr(logging_module, "dictConfig", fake_dict_config)

    logging_module.configure_logging("DEBUG")

    assert captured["version"] == 1
    assert captured["disable_existing_loggers"] is False
    assert captured["root"] == {"level": "DEBUG", "handlers": ["default"]}
    assert "default" in captured["handlers"]
    assert "default" in captured["formatters"]
