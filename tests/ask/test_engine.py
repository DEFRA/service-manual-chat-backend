import pytest

from app.ask import engine as engine_mod


class TestEngineSelection:
    def test_get_engine_defaults_to_stub(self) -> None:
        assert engine_mod.get_engine() is engine_mod.stub_engine

    def test_get_engine_selects_bedrock(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(engine_mod.app_config.config, "ask_engine", "bedrock")

        from app.ask import bedrock

        assert engine_mod.get_engine() is bedrock.bedrock_engine
