import logging
from pathlib import Path
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.roi import ROIFrame
from app.models.video import Video, VideoStatus
from app.schemas.roi import ROIFrameSchema, ROIResponse
from app.schemas.video import VideoStatusResponse, VideoUploadResponse
from app.services.storage import FileSizeLimitExceeded, save_upload
from app.worker.celery_app import celery_app

router = APIRouter()
logger = logging.getLogger("sentravision.routes")
settings = get_settings()


@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Handles video uploads. Validates the file extension/type, saves the raw file,
    stores the record in the database, and schedules processing with Celery.
    """
    logger.info("Incoming upload request: %s (Content-Type: %s)", file.filename, file.content_type)
    
    # Relaxed check: allows common video extensions even if content_type is generic
    is_video = (file.content_type and file.content_type.startswith("video/")) or \
               (file.filename and file.filename.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')))

    if not is_video:
        logger.warning("Upload rejected: file '%s' has invalid content type '%s'", file.filename, file.content_type)
        raise HTTPException(status_code=400, detail="Please upload a valid video file (.mp4, .mov, etc.)")

    original_name = file.filename or "uploaded_video.mp4"
    stored_name = f"{uuid.uuid4()}.mp4"
    try:
        stored_path = await save_upload(
            file=file,
            target_filename=stored_name,
            max_size_bytes=settings.max_upload_size_mb * 1024 * 1024,
        )
    except FileSizeLimitExceeded as exc:
        logger.error("Upload rejected: file size limit exceeded.", exc_info=exc)
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size of {settings.max_upload_size_mb}MB."
        ) from exc

    video = Video(
        original_filename=original_name,
        stored_filename=stored_name,
        status=VideoStatus.PENDING,
    )
    db.add(video)
    await db.flush()

    try:
        task = celery_app.send_task(
            "app.worker.tasks.process_video_task",
            args=[str(video.id), str(stored_path)],
        )
        video.celery_task_id = task.id
        video.status = VideoStatus.PROCESSING
        await db.commit()
        logger.info("Video %s queued for processing with task ID %s", video.id, task.id)
    except Exception as exc:
        logger.error("Failed to enqueue video processing task for video %s", video.id, exc_info=exc)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error scheduling video job")

    return VideoUploadResponse(
        video_id=video.id,
        job_id=task.id,
        status=video.status.value if hasattr(video.status, "value") else str(video.status),
        message="Upload accepted. Processing started.",
    )


@router.get("/video/{video_id}")
async def stream_processed_video(video_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Retrieves the processed video file for a completed job and streams it.
    """
    logger.debug("Request to stream processed video: %s", video_id)
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        logger.warning("Video ID %s not found in database", video_id)
        raise HTTPException(status_code=404, detail="Video not found")
    if video.status != VideoStatus.COMPLETED or not video.processed_filename:
        logger.warning("Video %s is not yet fully processed (status: %s)", video_id, video.status)
        raise HTTPException(status_code=409, detail="Video is not ready")

    path = settings.processed_dir / video.processed_filename
    if not path.exists():
        logger.error("Processed file missing on disk: %s", path)
        raise HTTPException(status_code=404, detail="Processed file missing")

    return FileResponse(path=str(path), media_type="video/mp4", filename=video.processed_filename)


@router.get("/roi/{video_id}", response_model=ROIResponse)
async def get_roi(
    video_id: uuid.UUID,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns pagination results of ROI detections (faces) for the requested video.
    """
    logger.debug("Requesting ROI frames for video %s (page=%d, page_size=%d)", video_id, page, page_size)
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1
    elif page_size > 100:
        page_size = 100

    video_result = await db.execute(select(Video).where(Video.id == video_id))
    video = video_result.scalar_one_or_none()
    if not video:
        logger.warning("Video %s not found during ROI retrieval", video_id)
        raise HTTPException(status_code=404, detail="Video not found")

    total_count = await db.scalar(
        select(func.count(ROIFrame.id)).where(ROIFrame.video_id == video_id)
    ) or 0

    offset = (page - 1) * page_size
    rows = (
        await db.execute(
            select(ROIFrame)
            .where(ROIFrame.video_id == video_id)
            .order_by(ROIFrame.frame_number.asc())
            .offset(offset)
            .limit(page_size)
        )
    ).scalars().all()

    total_frames = int(video.frame_count or 0)

    return ROIResponse(
        video_id=video_id,
        total_frames=total_frames,
        frames_with_faces=total_count,
        roi_data=[ROIFrameSchema.model_validate(r) for r in rows],
        page=page,
        page_size=page_size,
        total_count=total_count,
    )


@router.get("/status/{video_id}", response_model=VideoStatusResponse)
async def get_status(video_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Fetches the processing metadata and status of the video job.
    """
    logger.debug("Requesting status info for video %s", video_id)
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        logger.warning("Video %s not found during status check", video_id)
        raise HTTPException(status_code=404, detail="Video not found")

    return VideoStatusResponse(
        video_id=video.id,
        status=video.status.value if hasattr(video.status, "value") else str(video.status),
        original_filename=video.original_filename,
        duration_seconds=video.duration_seconds,
        fps=video.fps,
        frame_count=video.frame_count,
        width=video.width,
        height=video.height,
        faces_detected=video.faces_detected,
        processing_time_seconds=video.processing_time_seconds,
        error_message=video.error_message,
        created_at=video.created_at,
        updated_at=video.updated_at,
    )


@router.get("/health")
async def health():
    """
    Health check route for monitoring services.
    """
    return {"status": "ok"}

