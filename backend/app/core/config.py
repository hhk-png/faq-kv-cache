from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FAQ KV Cache Agent"

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # File storage
    data_dir: str = "data"
    faq_dataset_path: str = "data/faq_datasets/oncology"
    documents_dir: str = "data/documents"

    # LLM (OpenAI-compatible API)
    llm_api_key: str = "sk-your-api-key"
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_model: str = "deepseek-chat"
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.3

    # FAQ block settings
    faq_block_min_tokens: int = 100000
    faq_max_results: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
