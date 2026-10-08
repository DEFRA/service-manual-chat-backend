import pytest

from app.config import AppConfig


def test_ask_daily_ceiling_defaults_to_600(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASK_DAILY_CEILING", raising=False)
    assert AppConfig().ask_daily_ceiling == 600


def test_ask_daily_ceiling_is_read_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ASK_DAILY_CEILING", "5")
    assert AppConfig().ask_daily_ceiling == 5
