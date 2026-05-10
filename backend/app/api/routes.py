import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.roi import ROIFrame
from app.models.video import Video, VideoStatus
from app.schemas.roi import ROIFrameSchema, ROIResponse
from app.schemas.video import VideoStatusResponse, VideoUploadResponse
from app.services.storage import save_upload
from app.worker.celery_app import celery_app

router = APIRouter()


@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    print(f"Incoming upload: {file.filename} ({file.content_type})")
    
    # Relaxed check: allows common video extensions even if content_type is generic
    is_video = (file.content_type and file.content_type.startswith("video/")) or \
               (file.filename and file.filename.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')))

    if not is_video:
        print(f"Upload rejected: invalid content type {file.content_type}")
        raise HTTPException(status_code=400, detail="Please upload a valid video file (.mp4, .mov, etc.)")

    original_name = file.filename or "uploaded_video.mp4"
    stored_name = f"{uuid.uuid4()}.mp4"
    stored_path = await save_upload(file=file, target_filename=stored_name)

    video = Video(
        original_filename=original_name,
        stored_filename=stored_name,
        status=VideoStatus.PENDING,
    )
    db.add(video)
    await db.flush()

    task = celery_app.send_task(
        "app.worker.tasks.process_video_task",
        args=[str(video.id), str(stored_path)],
    )
    video.celery_task_id = task.id
    video.status = VideoStatus.PROCESSING

    return VideoUploadResponse(
        video_id=video.id,
        job_id=task.id,
        status=video.status.value if hasattr(video.status, "value") else str(video.status),
        message="Upload accepted. Processing started.",
    )


@router.get("/video/{video_id}")
async def stream_processed_video(video_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if video.status != VideoStatus.COMPLETED or not video.processed_filename:
        raise HTTPException(status_code=409, detail="Video is not ready")

    path = Path("/data/processed") / video.processed_filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Processed file missing")

    return FileResponse(path=str(path), media_type="video/mp4", filename=video.processed_filename)


@router.get("/roi/{video_id}", response_model=ROIResponse)
async def get_roi(video_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    video_result = await db.execute(select(Video).where(Video.id == video_id))
    video = video_result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    rows = (
        await db.execute(
            select(ROIFrame)
            .where(ROIFrame.video_id == video_id)
            .order_by(ROIFrame.frame_number.asc())
        )
    ).scalars().all()

    total_frames = int(video.frame_count or 0)
    frames_with_faces = len(rows)
    total_count = await db.scalar(
        select(func.count(ROIFrame.id)).where(ROIFrame.video_id == video_id)
    )

    return ROIResponse(
        video_id=video_id,
        total_frames=total_frames,
        frames_with_faces=frames_with_faces,
        roi_data=[ROIFrameSchema.model_validate(r) for r in rows],
        page=1,
        page_size=max(1, len(rows)),
        total_count=total_count or 0,
    )


@router.get("/status/{video_id}", response_model=VideoStatusResponse)
async def get_status(video_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
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
    return {"status": "ok"}
