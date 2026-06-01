from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FAQ KV Cache Agent"
    debug: bool = True

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # File storage
    data_dir: str = "data"
    faq_file: str = "data/faqs.json"
    documents_dir: str = "data/documents"
    cache_status_file: str = "data/cache_status.json"

    # LLM (OpenAI-compatible API)
    llm_api_key: str = "sk-your-api-key"
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_model: str = "deepseek-chat"
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.3

    # Redis & Celery (optional, disabled by default)
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    # FAQ block settings
    faq_block_min_tokens: int = 10000
    faq_max_results: int = 5
    faq_block_size: int = 25

    # Cache warm (legacy, kept for compatibility)
    cache_warm_debounce_seconds: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
