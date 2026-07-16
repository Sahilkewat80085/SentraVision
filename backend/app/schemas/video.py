"""SentraVision — Pydantic Schemas: Video"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class VideoUploadResponse(BaseModel):
    """
    Response schema returned upon successfully initiating a video upload.
    """
    video_id: uuid.UUID = Field(..., description="Unique database identifier for the uploaded video")
    job_id: str = Field(..., description="Celery background task job identifier")
    status: str = Field(..., description="Current processing status (e.g., PENDING, PROCESSING)")
    message: str = Field(..., description="Detailed status or confirmation message")


class VideoStatusResponse(BaseModel):
    """
    Detailed response schema showcasing video attributes, metrics, and processing errors.
    """
    model_config = ConfigDict(from_attributes=True)

    video_id: uuid.UUID = Field(..., description="Unique database identifier for the video")
    status: str = Field(..., description="Processing status of the video")
    original_filename: str = Field(..., description="Original filename of the uploaded video file")
    duration_seconds: float | None = Field(default=None, description="Duration of the video in seconds")
    fps: float | None = Field(default=None, description="Frames per second of the video")
    frame_count: int | None = Field(default=None, description="Total number of frames in the video")
    width: int | None = Field(default=None, description="Width of the video in pixels")
    height: int | None = Field(default=None, description="Height of the video in pixels")
    faces_detected: int | None = Field(default=None, description="Total number of faces detected in the video")
    processing_time_seconds: float | None = Field(default=None, description="Time spent processing the video in seconds")
    error_message: str | None = Field(default=None, description="Error message if processing failed")
    created_at: datetime = Field(..., description="Timestamp of when the video upload record was created")
    updated_at: datetime = Field(..., description="Timestamp of the last status update")


class VideoSummary(BaseModel):
    """
    Summarized representation of a video job, ideal for dashboard lists.
    """
    model_config = ConfigDict(from_attributes=True)

    video_id: uuid.UUID = Field(..., alias="id", description="Unique database identifier for the video")
    original_filename: str = Field(..., description="Original filename of the uploaded video")
    status: str = Field(..., description="Current processing status")
    created_at: datetime = Field(..., description="Timestamp of when the video record was created")

