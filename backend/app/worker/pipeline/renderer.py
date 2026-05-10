import logging
from pathlib import Path

import ffmpeg
from PIL import Image, ImageDraw

from app.config import get_settings
from app.worker.pipeline.detector import DetectionResult

logger = logging.getLogger(__name__)

settings = get_settings()


def draw_roi(frame_path: Path, detection: DetectionResult) -> None:
    if detection.bounding_box is None:
        return
    bbox = detection.bounding_box
    with Image.open(frame_path).convert("RGB") as image:
        draw = ImageDraw.Draw(image)
        draw.rectangle(
            [(bbox.x, bbox.y), (bbox.x + bbox.width, bbox.y + bbox.height)],
            outline=settings.roi_color,
            width=settings.roi_line_width,
        )
        image.save(frame_path, format="JPEG", quality=95)
    logger.debug(f"Drew ROI for {frame_path.name}")


def rebuild_video_from_frames(frames_dir: Path, output_path: Path, fps: float) -> None:
    pattern = str(frames_dir / "frame_%06d.jpg")
    
    # Use a safe fallback for FPS
    safe_fps = fps if (fps and fps > 0.1 and fps < 120) else 30.0
    
    try:
        logger.info(f"Rebuilding video: {pattern} at {safe_fps} FPS")
        
        # Most basic, standard H.264 output
        (
            ffmpeg
            .input(pattern, framerate=safe_fps, start_number=1)
            .output(
                str(output_path),
                vcodec="libx264",
                pix_fmt="yuv420p",
                movflags="+faststart",
                an=None,  # No audio
                vf="scale='trunc(iw/2)*2:trunc(ih/2)*2'" # Simple scale to even dims
            )
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as exc:
        err_msg = exc.stderr.decode() if exc.stderr else "Unknown FFmpeg error"
        logger.error(f"FFmpeg rebuild failed: {err_msg}")
        raise
