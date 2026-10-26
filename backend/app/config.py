"""Application configuration for local development."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+psycopg://workbench_user:local_only_dev_password@localhost:5432/workbench_db"
    )
    ollama_base_url: str = "http://localhost:11434"
    ollama_embed_model: str = "nomic-embed-text"
    max_upload_mb: int = 15
    frontend_origin: str = "http://localhost:5173"

    # Run the backend with the terminal's current directory set to backend/.
    # In that case ../.env refers to the repository-root .env file.
    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()
