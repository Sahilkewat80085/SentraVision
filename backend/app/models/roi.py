"""SentraVision — ROI Frame ORM Model"""
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ROIFrame(Base):
    """
    Stores per-frame Region of Interest (ROI) face detection bounding box data.
    Maps to the 'roi_frames' database table.
    """
    __tablename__ = "roi_frames"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    frame_number: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[float] = mapped_column(Float, nullable=False)  # Offset in seconds from video start

    # Bounding box coordinates and dimensions (in pixels relative to original resolution)
    x: Mapped[int] = mapped_column(Integer, nullable=False)
    y: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)

    # Detection confidence score [0.0, 1.0] from detection engine
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationship back to Video parent
    video: Mapped["Video"] = relationship(  # noqa: F821
        "Video", back_populates="roi_frames"
    )

    # Composite index for rapid query execution during playback and pagination
    __table_args__ = (
        Index("ix_roi_frames_video_frame", "video_id", "frame_number"),
        Index("ix_roi_frames_video_timestamp", "video_id", "timestamp"),
    )

    def __repr__(self) -> str:
        return (
            f"<ROIFrame id={self.id} video_id={self.video_id} frame={self.frame_number} "
            f"bbox=({self.x},{self.y},{self.width},{self.height}) confidence={self.confidence}>"
        )
