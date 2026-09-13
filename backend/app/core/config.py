from functools import lru_cache
from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "DataPilot-Agent V4"
    app_env: str = "development"
    api_prefix: str = "/api"
    secret_key: str = "change-me"
    cors_origins: list[str] | str = ["http://localhost:5173", "http://localhost:8080"]

    database_url: str = "postgresql+psycopg://datapilot:datapilot123@localhost:5432/datapilot"
    redis_url: str = "redis://localhost:6379/0"

    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-v4-flash"
    deepseek_base_url: str = ""
    llm_temperature: float = 0.1

    upload_dir: str = "data/uploads"
    chart_dir: str = "outputs/charts"
    report_dir: str = "outputs/reports"
    max_upload_mb: int = 50
    max_agent_steps: int = 12
    max_retry: int = 2
    sql_timeout_ms: int = 5000
    sandbox_url: str = "http://localhost:8001"
    sandbox_timeout_seconds: int = 8

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value):
        if isinstance(value, str):
            return [x.strip() for x in value.split(",") if x.strip()]
        return value

    def ensure_dirs(self) -> None:
        for p in (self.upload_dir, self.chart_dir, self.report_dir):
            Path(p).mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
