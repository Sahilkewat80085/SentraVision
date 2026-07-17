"""SentraVision — Pydantic Schemas: ROI"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ROIFrameSchema(BaseModel):
    """
    ROI bounding box for a single face detection within a frame.
    Coordinates and dimensions are in pixels relative to the original frame.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique database identifier for the detection record")
    video_id: uuid.UUID = Field(..., description="Reference UUID to the parent video model")
    frame_number: int = Field(..., ge=0, description="The zero-indexed frame number containing the detection")
    timestamp: float = Field(..., ge=0.0, description="Time offset in seconds from the start of the video")
    x: int = Field(..., ge=0, description="Left coordinate (x) of bounding box in pixels")
    y: int = Field(..., ge=0, description="Top coordinate (y) of bounding box in pixels")
    width: int = Field(..., gt=0, description="Width of bounding box in pixels")
    height: int = Field(..., gt=0, description="Height of bounding box in pixels")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model prediction confidence score")
    created_at: datetime = Field(..., description="Timestamp of when this detection was recorded")


class ROIResponse(BaseModel):
    """
    Paginated API response container listing ROI detections for a given video.
    """
    video_id: uuid.UUID = Field(..., description="UUID of the queried video")
    total_frames: int = Field(..., ge=0, description="Total number of frames in the video")
    frames_with_faces: int = Field(..., ge=0, description="Count of frames with at least one detected face")
    roi_data: list[ROIFrameSchema] = Field(..., description="Paginated list of detected frame bounding boxes")
    page: int = Field(..., ge=1, description="Current page index")
    page_size: int = Field(..., ge=1, le=100, description="Number of items returned per page")
    total_count: int = Field(..., ge=0, description="Grand total count of ROI frames found")

