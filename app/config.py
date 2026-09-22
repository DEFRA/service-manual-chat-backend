from typing import Literal

from pydantic import HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict()
    python_env: str | None = None
    host: str = "127.0.0.1"
    port: int = 8086
    log_config: str | None = None
    mongo_uri: str | None = None
    mongo_database: str = "service-manual-chat-backend"
    mongo_truststore: str = "TRUSTSTORE_CDP_ROOT_CA"
    aws_endpoint_url: str | None = None
    http_proxy: HttpUrl | None = None
    enable_metrics: bool = False
    tracing_header: str = "x-cdp-request-id"
    # What answers /ask. stub needs no key; bedrock needs AWS_BEARER_TOKEN_BEDROCK
    # locally or an inference profile on CDP.
    ask_engine: Literal["stub", "bedrock"] = "stub"
    # Model id locally (the sandbox takes plain ids); an inference profile id
    # or ARN on CDP. eu-west-2 is London; no cross-region inference.
    bedrock_model_id: str = "anthropic.claude-sonnet-4-6"
    bedrock_region: str = "eu-west-2"
    # Models that return 403 "your request did not allow prompt caching" when
    # sent a cache point. Comma separated, matched as a substring of the model
    # id so an inference profile ARN carrying the id is caught too.
    bedrock_models_without_prompt_caching: str = "anthropic.claude-3-haiku"
    # Empty locally. On CDP the platform gives one guardrail per profile.
    bedrock_guardrail_id: str | None = None
    bedrock_guardrail_version: str | None = None
    # The toolkit pages the model answers from and the prompt it follows.
    content_dir: str = "content"
    system_prompt_path: str = "prompts/system.md"


config = AppConfig()
