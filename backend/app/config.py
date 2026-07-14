"""
SentraVision — Application Configuration
Loaded from environment variables via Pydantic BaseSettings.
"""
from functools import lru_cache
from pathlib import Path
from typing import List, Tuple

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── App ──────────────────────────────────────────────────────────
    app_name: str = Field(default="SentraVision", description="Name of the application")
    app_version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=False, description="Enable debug mode")
    allowed_origins: List[str] = Field(
        default=["http://localhost", "http://localhost:5173"],
        description="Allowed origins for CORS"
    )

    # ── Database ─────────────────────────────────────────────────────
    postgres_user: str = Field(default="sentravision", description="PostgreSQL username")
    postgres_password: str = Field(default="sentravision_secret", description="PostgreSQL password")
    postgres_db: str = Field(default="sentravision", description="PostgreSQL database name")
    postgres_host: str = Field(default="postgres", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")

    @property
    def database_url(self) -> str:
        """
        Generate asynchronous database connection URL.
        """
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sync_database_url(self) -> str:
        """
        Generate synchronous database connection URL.
        """
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ── Redis / Celery ────────────────────────────────────────────────
    redis_host: str = Field(default="redis", description="Redis host name")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_db: int = Field(default=0, description="Redis database index")

    @property
    def redis_url(self) -> str:
        """
        Generate Redis URL.
        """
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def celery_broker_url(self) -> str:
        """
        Get Celery broker connection URL.
        """
        return self.redis_url

    @property
    def celery_result_backend(self) -> str:
        """
        Get Celery backend connection URL.
        """
        return self.redis_url

    # ── Storage ───────────────────────────────────────────────────────
    upload_dir: Path = Field(default=Path("/data/uploads"), description="Directory for upload files")
    processed_dir: Path = Field(default=Path("/data/processed"), description="Directory for processed files")
    frames_dir: Path = Field(default=Path("/data/frames"), description="Directory for extracted frames")
    max_upload_size_mb: int = Field(default=500, description="Maximum video upload size in MB")

    # ── Processing ────────────────────────────────────────────────────
    face_detection_confidence: float = Field(default=0.5, description="Confidence threshold for face detection")
    roi_line_width: int = Field(default=3, description="Line width for ROI indicators")
    roi_color: Tuple[int, int, int] = Field(default=(0, 255, 128), description="RGB Neon green color for ROI")
    frame_extraction_fps: int = Field(default=0, description="FPS for extraction (0 = native)")

    # ── Security ──────────────────────────────────────────────────────
    secret_key: str = Field(default="change-me-in-production-please", description="Application secret key")
    api_key_header: str = Field(default="X-SentraVision-Key", description="HTTP header key name for API Key validation")


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.
    """
    return Settings()

