"""SentraVision — Video Job ORM Model"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class VideoStatus(str, PyEnum):
    """
    Represents the processing state of a video job.
    """
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Video(Base):
    """
    Database representation of a video upload job and its extracted properties.
    Tracks state, Celery task assignment, video specs, and processing outcomes.
    """
    __tablename__ = "videos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    processed_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[str] = mapped_column(
        Enum(VideoStatus, name="video_status"),
        default=VideoStatus.PENDING,
        nullable=False,
        index=True,
    )
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Video properties / metadata
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    fps: Mapped[float | None] = mapped_column(Float, nullable=True)
    frame_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Job metrics / processing metadata
    faces_detected: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processing_time_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    roi_frames: Mapped[list["ROIFrame"]] = relationship(  # noqa: F821
        "ROIFrame", back_populates="video", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Video id={self.id} original_filename={self.original_filename} status={self.status}>"

