"""
SentraVision — Frame Extractor
Uses ffmpeg-python (NOT OpenCV) to extract individual frames from a video.
"""
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Union

import ffmpeg

logger = logging.getLogger("sentravision.pipeline.extractor")


class FrameExtractionError(Exception):
    """
    Custom exception raised when video metadata extraction or frame splitting fails.
    """
    pass


def get_video_metadata(video_path: Path) -> Dict[str, Union[int, float, str]]:
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
        try:
            num, den = fps_str.split("/")
            fps = float(num) / float(den) if float(den) != 0 else 30.0
        except (ValueError, ZeroDivisionError):
            fps = 30.0

        if fps <= 0:
            fps = 30.0

        duration = float(probe["format"].get("duration", 0))
        frame_count_str = video_stream.get("nb_frames")
        try:
            frame_count = int(frame_count_str) if frame_count_str else int(fps * duration)
        except (ValueError, TypeError):
            frame_count = 0

        logger.info(
            "Metadata for %s: %.2f FPS, %.2fs, %d frames",
            video_path.name,
            fps,
            duration,
            frame_count
        )

        return {
            "fps": round(fps, 3),
            "duration_seconds": round(duration, 3),
            "frame_count": frame_count,
            "width": int(video_stream["width"]),
            "height": int(video_stream["height"]),
            "codec": video_stream.get("codec_name", "unknown"),
        }
    except ffmpeg.Error as exc:
        err_msg = exc.stderr.decode() if exc.stderr else "Unknown ffprobe error"
        raise FrameExtractionError(f"ffprobe failed: {err_msg}") from exc


def extract_frames(
    video_path: Path,
    output_dir: Path,
    fps: int = 0,
) -> List[Path]:
    """
    Extract frames from a video using ffmpeg-python.

    Args:
        video_path:  Source video file path.
        output_dir:  Directory where JPEG frames will be written.
        fps:         Target FPS (0 = native fps).

    Returns:
        Sorted list of extracted frame file paths.
    """
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        raise FrameExtractionError(f"Failed to create extraction folder: {exc}") from exc

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
        err_msg = exc.stderr.decode() if exc.stderr else "Unknown ffmpeg error"
        raise FrameExtractionError(
            f"Frame extraction failed: {err_msg}"
        ) from exc

    frames = sorted(output_dir.glob("frame_*.jpg"))
    logger.info("Extracted %d frames from %s", len(frames), video_path.name)
    return frames


def cleanup_frames(frames_dir: Path) -> None:
    """
    Remove temporary frame directory.
    """
    if frames_dir.exists():
        try:
            shutil.rmtree(frames_dir)
            logger.debug("Cleaned up frames directory: %s", frames_dir)
        except Exception as exc:
            logger.error("Failed to clean up frames directory: %s", frames_dir, exc_info=exc)

