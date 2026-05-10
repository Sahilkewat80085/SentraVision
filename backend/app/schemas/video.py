"""SentraVision — Pydantic Schemas: Video"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class VideoUploadResponse(BaseModel):
    video_id: uuid.UUID
    job_id: str
    status: str
    message: str


class VideoStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    video_id: uuid.UUID
    status: str
    original_filename: str
    duration_seconds: float | None = None
    fps: float | None = None
    frame_count: int | None = None
    width: int | None = None
    height: int | None = None
    faces_detected: int | None = None
    processing_time_seconds: float | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class VideoSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    video_id: uuid.UUID = Field(alias="id")
    original_filename: str
    status: str
    created_at: datetime
