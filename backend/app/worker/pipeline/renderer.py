from pathlib import Path

import ffmpeg
from PIL import Image, ImageDraw

from app.config import get_settings
from app.worker.pipeline.detector import DetectionResult

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


def rebuild_video_from_frames(frames_dir: Path, output_path: Path, fps: float) -> None:
    pattern = str(frames_dir / "frame_%06d.jpg")
    stream = ffmpeg.input(pattern, framerate=max(1.0, fps))
    stream = ffmpeg.output(
        stream,
        str(output_path),
        vcodec="libx264",
        pix_fmt="yuv420p",
        movflags="+faststart",
    )
    ffmpeg.run(stream, overwrite_output=True, quiet=True)
