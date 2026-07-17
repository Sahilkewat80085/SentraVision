"""
SentraVision — Celery Background Tasks
"""
import logging
import time
import uuid
from pathlib import Path

from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.roi import ROIFrame
from app.models.video import Video, VideoStatus
from app.worker.celery_app import celery_app
from app.worker.pipeline.detector import detect_faces_in_frames
from app.worker.pipeline.extractor import cleanup_frames, extract_frames, get_video_metadata
from app.worker.pipeline.renderer import draw_roi, rebuild_video_from_frames

logger = logging.getLogger("sentravision.tasks")
settings = get_settings()

# Initialize synchronous engine for Celery tasks since tasks run in a sync worker context
sync_engine = create_engine(settings.sync_database_url, pool_pre_ping=True)


@celery_app.task(name="app.worker.tasks.process_video_task", bind=True, max_retries=2)
def process_video_task(self, video_id: str, uploaded_path: str) -> None:
    """
    Celery background job task to process uploaded videos.
    Extracts frames, performs face detection, populates detected ROI bounding boxes,
    re-renders the video with ROIs outlined, and updates the task database status.
    """
    started = time.perf_counter()
    vid = uuid.UUID(video_id)
    source = Path(uploaded_path)
    frame_dir = settings.frames_dir / str(vid)
    processed_name = f"{vid}_processed.mp4"
    processed_path = settings.processed_dir / processed_name

    logger.info("Celery task started: Processing video %s from path %s", vid, uploaded_path)

    with Session(sync_engine) as db:
        video = db.get(Video, vid)
        if not video:
            logger.error("Abort task: Video record %s not found in database.", vid)
            return
            
        video.status = VideoStatus.PROCESSING
        db.commit()

        try:
            # Step 1: Extract Metadata
            logger.info("Extracting metadata for video %s", vid)
            metadata = get_video_metadata(source)
            
            # Step 2: Extract Frames
            logger.info("Extracting frames to %s", frame_dir)
            frames = extract_frames(source, frame_dir, fps=settings.frame_extraction_fps)
            
            if not frames:
                logger.error("Failed to extract frames for video %s", vid)
                raise ValueError("Video extraction yielded 0 frames. Check if the source file is a valid video.")

            logger.info("Extracted %d frames. Running face detection pipeline...", len(frames))
            
            # Step 3: Run Detection Pipeline
            detections = detect_faces_in_frames(
                frames,
                fps=float(metadata["fps"]),
                min_confidence=settings.face_detection_confidence,
            )

            # Clean any previously existing ROI frames for this video to ensure idempotency
            db.execute(delete(ROIFrame).where(ROIFrame.video_id == vid))
            faces_detected = 0

            # Step 4: Render Bounding Boxes & Save detections
            logger.info("Rendering ROI overlays and saving bounding boxes...")
            for frame_path, detection in zip(frames, detections):
                draw_roi(frame_path, detection)
                if detection.bounding_box is None:
                    continue
                faces_detected += 1
                box = detection.bounding_box
                db.add(
                    ROIFrame(
                        video_id=vid,
                        frame_number=detection.frame_number,
                        timestamp=detection.timestamp,
                        x=box.x,
                        y=box.y,
                        width=box.width,
                        height=box.height,
                        confidence=box.confidence,
                    )
                )

            # Step 5: Rebuild Video File
            logger.info("Rebuilding processed video to %s", processed_path)
            rebuild_video_from_frames(frame_dir, processed_path, fps=float(metadata["fps"]))

            # Step 6: Mark Completion Status in Database
            video.processed_filename = processed_name
            video.status = VideoStatus.COMPLETED
            video.duration_seconds = float(metadata["duration_seconds"])
            video.fps = float(metadata["fps"])
            video.frame_count = int(metadata["frame_count"])
            video.width = int(metadata["width"])
            video.height = int(metadata["height"])
            video.faces_detected = faces_detected
            video.processing_time_seconds = round(time.perf_counter() - started, 3)
            video.error_message = None
            db.commit()
            
            logger.info("Video %s processed successfully in %.3f seconds. Detected %d faces.",
                        vid, video.processing_time_seconds, faces_detected)
            
        except Exception as exc:
            logger.error("Exception encountered processing video %s", vid, exc_info=exc)
            video.status = VideoStatus.FAILED
            video.error_message = str(exc)
            video.processing_time_seconds = round(time.perf_counter() - started, 3)
            db.commit()
            raise
        finally:
            logger.info("Cleaning up temporary frame directory: %s", frame_dir)
            cleanup_frames(frame_dir)

