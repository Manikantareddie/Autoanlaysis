from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded only from backend environment configuration."""

    app_name: str = "InsightPilot AI"
    app_env: str = "development"
    cors_origins: str = "https://autoanlaysis.vercel.app,http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"
    max_upload_size_mb: int = 25
    max_dataset_rows: int = 100_000
    storage_dir: Path = Path(__file__).resolve().parents[3] / "storage" / "datasets"
    database_url: str = "sqlite:///./insightpilot.db"
    embedding_provider: str = "deterministic"
    llm_provider: str = "nvidia"
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "nvidia/nemotron-3.5-bolt-e4b"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"

    model_config = SettingsConfigDict(
        env_file=(
            Path(__file__).resolve().parents[2] / ".env",
            Path(__file__).resolve().parents[3] / ".env",
            ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

