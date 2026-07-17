"""
SentraVision — Video ROI Renderer
Draws detected face ROI bounding boxes back onto image frames and encodes them into a video.
"""
import logging
from pathlib import Path

import ffmpeg
from PIL import Image, ImageDraw

from app.config import get_settings
from app.worker.pipeline.detector import DetectionResult

logger = logging.getLogger("sentravision.pipeline.renderer")
settings = get_settings()


def draw_roi(frame_path: Path, detection: DetectionResult) -> None:
    """
    Draws a single bounding box overlay onto the target frame file.
    Saves the updated frame as JPEG format.
    """
    if detection.bounding_box is None:
        return
    
    bbox = detection.bounding_box
    try:
        with Image.open(frame_path).convert("RGB") as image:
            draw = ImageDraw.Draw(image)
            draw.rectangle(
                [(bbox.x, bbox.y), (bbox.x + bbox.width, bbox.y + bbox.height)],
                outline=settings.roi_color,
                width=settings.roi_line_width,
            )
            image.save(frame_path, format="JPEG", quality=95)
        logger.debug("Drew ROI bounding box for frame: %s", frame_path.name)
    except Exception as exc:
        logger.error("Failed to draw ROI overlay on frame: %s", frame_path, exc_info=exc)
        raise


def rebuild_video_from_frames(frames_dir: Path, output_path: Path, fps: float) -> None:
    """
    Uses ffmpeg to compile processed JPEG frames back into a single MP4 video file.
    Applies standard H.264 video codec and formats appropriate dimension scaling.
    """
    # Ensure destination parent directory exists
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        logger.error("Failed to create destination folder for rebuilt video: %s", output_path.parent, exc_info=exc)
        raise

    pattern = str(frames_dir / "frame_%06d.jpg")
    
    # Use a safe fallback for FPS
    safe_fps = fps if (fps and fps > 0.1 and fps < 120) else 30.0
    
    try:
        logger.info("Rebuilding video stream: %s at %.2f FPS", pattern, safe_fps)
        
        # Most basic, standard H.264 output
        (
            ffmpeg
            .input(pattern, framerate=safe_fps, start_number=1)
            .output(
                str(output_path),
                vcodec="libx264",
                pix_fmt="yuv420p",
                movflags="+faststart",
                an=None,  # No audio stream
                vf="scale='trunc(iw/2)*2:trunc(ih/2)*2'"  # Force even dimensions for H.264
            )
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        logger.info("Successfully rebuilt processed video at: %s", output_path)
    except ffmpeg.Error as exc:
        err_msg = exc.stderr.decode() if exc.stderr else "Unknown FFmpeg error"
        logger.error("FFmpeg rebuild failed: %s", err_msg)
        raise

