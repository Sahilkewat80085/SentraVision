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

settings = get_settings()
sync_engine = create_engine(settings.sync_database_url, pool_pre_ping=True)


@celery_app.task(name="app.worker.tasks.process_video_task", bind=True, max_retries=2)
def process_video_task(self, video_id: str, uploaded_path: str):
    started = time.perf_counter()
    vid = uuid.UUID(video_id)
    source = Path(uploaded_path)
    frame_dir = settings.frames_dir / str(vid)
    processed_name = f"{vid}_processed.mp4"
    processed_path = settings.processed_dir / processed_name

    with Session(sync_engine) as db:
        video = db.get(Video, vid)
        if not video:
            return
        video.status = VideoStatus.PROCESSING
        db.commit()

        try:
            metadata = get_video_metadata(source)
            frames = extract_frames(source, frame_dir, fps=settings.frame_extraction_fps)
            detections = detect_faces_in_frames(
                frames,
                fps=float(metadata["fps"]),
                min_confidence=settings.face_detection_confidence,
            )

            db.execute(delete(ROIFrame).where(ROIFrame.video_id == vid))
            faces_detected = 0

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

            rebuild_video_from_frames(frame_dir, processed_path, fps=float(metadata["fps"]))

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
        except Exception as exc:
            video.status = VideoStatus.FAILED
            video.error_message = str(exc)
            video.processing_time_seconds = round(time.perf_counter() - started, 3)
            db.commit()
            raise
        finally:
            cleanup_frames(frame_dir)
