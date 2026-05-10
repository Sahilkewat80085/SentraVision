"""SentraVision — Pydantic Schemas: ROI"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ROIFrameSchema(BaseModel):
    """
    ROI bounding box for a single frame.
    Coordinates are in pixels relative to the original frame dimensions.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    video_id: uuid.UUID
    frame_number: int
    timestamp: float = Field(..., description="Time offset in seconds")
    x: int = Field(..., description="Left edge of bounding box")
    y: int = Field(..., description="Top edge of bounding box")
    width: int = Field(..., description="Width of bounding box")
    height: int = Field(..., description="Height of bounding box")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    created_at: datetime


class ROIResponse(BaseModel):
    video_id: uuid.UUID
    total_frames: int
    frames_with_faces: int
    roi_data: list[ROIFrameSchema]
    page: int
    page_size: int
    total_count: int
