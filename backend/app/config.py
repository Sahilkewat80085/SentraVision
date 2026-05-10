"""
SentraVision — Application Configuration
Loaded from environment variables via Pydantic BaseSettings.
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── App ──────────────────────────────────────────────────────────
    app_name: str = "SentraVision"
    app_version: str = "1.0.0"
    debug: bool = False
    allowed_origins: list[str] = ["http://localhost", "http://localhost:5173"]

    # ── Database ─────────────────────────────────────────────────────
    postgres_user: str = "sentravision"
    postgres_password: str = "sentravision_secret"
    postgres_db: str = "sentravision"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sync_database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ── Redis / Celery ────────────────────────────────────────────────
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def celery_broker_url(self) -> str:
        return self.redis_url

    @property
    def celery_result_backend(self) -> str:
        return self.redis_url

    # ── Storage ───────────────────────────────────────────────────────
    upload_dir: Path = Path("/data/uploads")
    processed_dir: Path = Path("/data/processed")
    frames_dir: Path = Path("/data/frames")
    max_upload_size_mb: int = 500

    # ── Processing ────────────────────────────────────────────────────
    face_detection_confidence: float = 0.5
    roi_line_width: int = 3
    roi_color: tuple[int, int, int] = (0, 255, 128)  # Neon green
    frame_extraction_fps: int = 0                     # 0 = native fps

    # ── Security ──────────────────────────────────────────────────────
    secret_key: str = "change-me-in-production-please"
    api_key_header: str = "X-SentraVision-Key"


@lru_cache
def get_settings() -> Settings:
    return Settings()
