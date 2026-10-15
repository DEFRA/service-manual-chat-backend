import pytest

from app import config


def test_ask_daily_ceiling_defaults_to_600(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASK_DAILY_CEILING", raising=False)
    assert config.AppConfig().ask_daily_ceiling == 600


def test_ask_daily_ceiling_is_read_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ASK_DAILY_CEILING", "5")
    assert config.AppConfig().ask_daily_ceiling == 5


def test_ask_daily_usage_ttl_seconds_defaults_to_90_days(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ASK_DAILY_USAGE_TTL_SECONDS", raising=False)
    assert config.AppConfig().ask_daily_usage_ttl_seconds == 90 * 24 * 60 * 60


def test_ask_daily_usage_ttl_seconds_is_read_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ASK_DAILY_USAGE_TTL_SECONDS", "60")
    assert config.AppConfig().ask_daily_usage_ttl_seconds == 60
