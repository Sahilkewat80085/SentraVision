"""
SentraVision — Pydantic Validation Schemas
Exposes schemas representing upload responses, statuses, and ROI detections.
"""
from app.schemas.video import VideoUploadResponse, VideoStatusResponse, VideoSummary
from app.schemas.roi import ROIFrameSchema, ROIResponse

__all__ = [
    "VideoUploadResponse",
    "VideoStatusResponse",
    "VideoSummary",
    "ROIFrameSchema",
    "ROIResponse",
]

