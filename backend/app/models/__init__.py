"""
SentraVision — Database Declarative Models
Exposes core tables representing Video files and ROI detections.
"""
from app.models.video import Video, VideoStatus
from app.models.roi import ROIFrame

__all__ = ["Video", "VideoStatus", "ROIFrame"]

