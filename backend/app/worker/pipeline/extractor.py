"""
SentraVision — Frame Extractor
Uses ffmpeg-python (NOT OpenCV) to extract individual frames from a video.
"""
import json
import logging
import shutil
import subprocess
from pathlib import Path

import ffmpeg

logger = logging.getLogger(__name__)


class FrameExtractionError(Exception):
    pass


def get_video_metadata(video_path: Path) -> dict:
    """
    Probe the video file to extract metadata (fps, duration, dimensions).
    Uses ffprobe (bundled with ffmpeg-python).
    """
    try:
        probe = ffmpeg.probe(str(video_path))
        video_stream = next(
            (s for s in probe["streams"] if s["codec_type"] == "video"), None
        )
        if not video_stream:
            raise FrameExtractionError("No video stream found in file.")

        # Parse FPS — stored as a fraction string like "30000/1001"
        fps_str = video_stream.get("r_frame_rate", "30/1")
        num, den = fps_str.split("/")
        fps = float(num) / float(den)

        duration = float(probe["format"].get("duration", 0))
        frame_count_str = video_stream.get("nb_frames")
        frame_count = int(frame_count_str) if frame_count_str else int(fps * duration)

        return {
            "fps": round(fps, 3),
            "duration_seconds": round(duration, 3),
            "frame_count": frame_count,
            "width": int(video_stream["width"]),
            "height": int(video_stream["height"]),
            "codec": video_stream.get("codec_name", "unknown"),
        }
    except ffmpeg.Error as exc:
        raise FrameExtractionError(f"ffprobe failed: {exc.stderr.decode()}") from exc


def extract_frames(
    video_path: Path,
    output_dir: Path,
    fps: int = 0,
) -> list[Path]:
    """
    Extract frames from a video using ffmpeg-python.

    Args:
        video_path:  Source video file path.
        output_dir:  Directory where JPEG frames will be written.
        fps:         Target FPS (0 = native fps).

    Returns:
        Sorted list of extracted frame file paths.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_pattern = str(output_dir / "frame_%06d.jpg")

    stream = ffmpeg.input(str(video_path))

    if fps and fps > 0:
        stream = stream.filter("fps", fps=fps)

    stream = ffmpeg.output(
        stream,
        output_pattern,
        format="image2",
        vcodec="mjpeg",
        **{"qscale:v": 2},  # High quality JPEG
    )

    try:
        ffmpeg.run(stream, overwrite_output=True, quiet=True)
    except ffmpeg.Error as exc:
        raise FrameExtractionError(
            f"Frame extraction failed: {exc.stderr.decode()}"
        ) from exc

    frames = sorted(output_dir.glob("frame_*.jpg"))
    logger.info(f"Extracted {len(frames)} frames from {video_path.name}")
    return frames


def cleanup_frames(frames_dir: Path) -> None:
    """Remove temporary frame directory."""
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
        logger.debug(f"Cleaned up frames directory: {frames_dir}")
