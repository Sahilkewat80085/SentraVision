# SentraVision

Production-style distributed video face-ROI platform using FastAPI, Celery, Redis, PostgreSQL, MediaPipe, Pillow, and ffmpeg (no OpenCV).

## 1) High-Level Architecture

- Frontend uploads a video and polls processing status.
- FastAPI stores video metadata and enqueues a Celery job.
- Celery worker extracts frames with ffmpeg, runs MediaPipe face detection per frame, draws axis-aligned ROI rectangles via Pillow, rebuilds processed MP4 via ffmpeg, and persists ROI rows in PostgreSQL.
- Nginx reverse proxies `/api/*` to backend and web UI to frontend.

See full diagrams in [docs/architecture.md](/C:/Users/kkewa/Downloads/SentraVision/docs/architecture.md).

## 2) Directory Tree

```text
SentraVision/
├─ backend/
│  ├─ app/
│  │  ├─ api/routes.py
│  │  ├─ models/{video.py,roi.py}
│  │  ├─ schemas/{video.py,roi.py}
│  │  ├─ services/storage.py
│  │  ├─ worker/
│  │  │  ├─ celery_app.py
│  │  │  ├─ tasks.py
│  │  │  └─ pipeline/{extractor.py,detector.py,renderer.py}
│  │  ├─ config.py
│  │  ├─ database.py
│  │  └─ main.py
│  ├─ requirements.txt
│  ├─ Dockerfile
│  └─ .env.example
├─ frontend/
│  ├─ src/{App.jsx,api.js,main.jsx,styles.css}
│  ├─ package.json
│  ├─ Dockerfile
│  ├─ vite.config.js
│  ├─ tailwind.config.js
│  └─ postcss.config.js
├─ nginx/default.conf
├─ docs/architecture.md
├─ docker-compose.yml
└─ README.md
```

## 3) API

### `POST /api/upload`
- Input: `multipart/form-data` with `file` (video)
- Output:
```json
{
  "video_id": "uuid",
  "job_id": "celery-task-id",
  "status": "PROCESSING",
  "message": "Upload accepted. Processing started."
}
```

### `GET /api/video/{video_id}`
- Streams processed MP4 if completed, else `409`.

### `GET /api/roi/{video_id}`
- Returns ROI rows:
```json
{
  "video_id": "uuid",
  "total_frames": 120,
  "frames_with_faces": 95,
  "roi_data": [
    {
      "video_id": "uuid",
      "frame_number": 24,
      "timestamp": 1.24,
      "x": 120,
      "y": 80,
      "width": 220,
      "height": 220,
      "confidence": 0.98
    }
  ],
  "page": 1,
  "page_size": 95,
  "total_count": 95
}
```

### Optional endpoints included
- `GET /api/status/{video_id}`
- `GET /api/health`

## 4) Video Pipeline

1. Save upload to `/data/uploads`.
2. Enqueue Celery task with `video_id` + file path.
3. ffprobe metadata (`fps`, `duration`, dimensions).
4. ffmpeg frame extraction (`frame_000001.jpg`, ...).
5. MediaPipe FaceDetection per frame; choose highest-confidence face.
6. Convert normalized bbox -> minimal axis-aligned absolute rectangle.
7. Draw ROI rectangle via `PIL.ImageDraw.rectangle`.
8. Persist frame ROI rows in `roi_frames`.
9. Rebuild MP4 from modified frames with H.264 (`yuv420p`, `+faststart`).
10. Update video status to `COMPLETED`.

## 5) Why these design choices

- Celery + Redis decouples heavy CV workload from API latency.
- PostgreSQL provides relational guarantees and indexed temporal ROI queries.
- MediaPipe gives robust face detection without OpenCV/Haar.
- ffmpeg frame IO is battle-tested and production-efficient.
- Separate worker container supports horizontal scaling independently from API.
- Nginx centralizes upload body limits and reverse-proxy concerns.

## 6) Performance optimizations

- `worker_prefetch_multiplier=1` for fair task scheduling.
- `task_acks_late=True` for reliability on worker failures.
- Indexed `(video_id, frame_number)` and `(video_id, timestamp)` on ROI table.
- JPEG frame quality controlled for speed/quality tradeoff.
- MP4 rebuild with `+faststart` for quicker browser playback.

## 7) Security considerations

- Restrict upload type to `video/*`.
- Store files with UUID filenames to avoid path traversal.
- Keep containers on private Docker network behind Nginx.
- Secrets via env vars (`POSTGRES_PASSWORD`, `SECRET_KEY`).
- Enforce `client_max_body_size` in Nginx.

## 8) Scalability strategy

- Add workers (`docker compose up --scale worker=4`) for throughput.
- Move `/data` from Docker volume to S3-compatible object storage.
- Replace status polling with WebSocket/SSE and Redis pub/sub.
- Use dedicated autoscaling queue tiers by video duration.

## 9) Logging and error handling

- Task failures mark video `FAILED` with `error_message`.
- API returns explicit `404/409/400` states for lifecycle clarity.
- Add structured logging (already prepared dependency: `structlog`) for production enrichment.

## 10) Recruiter-impressive enhancements included

- Distributed async pipeline (API + queue + worker).
- Non-blocking FastAPI endpoints with explicit job IDs.
- Frame-level ROI persistence for analytics and replay.
- Diagrammed architecture and ER model.
- Containerized 5-service stack with reverse proxy.
- Clear extension points: WebSocket updates, cloud object storage, auth, and tracing.

## 11) Run Locally (Docker)

1. Copy env:
```bash
cp .env.example .env
```
2. Start stack:
```bash
docker compose up --build
```
3. Open UI:
- [http://localhost:8080](http://localhost:8080)
4. API docs:
- [http://localhost:8080/docs](http://localhost:8080/docs)

## 12) Deployment Notes

- Build immutable images in CI and push to registry.
- Use managed Postgres/Redis in staging/prod.
- Mount persistent shared storage for `/data/processed` and `/data/uploads`.
- Put Nginx behind cloud LB with TLS termination.
- Add observability: Prometheus + Grafana + OpenTelemetry tracing.

## 13) Frontend UX mock

- Upload panel with job + video IDs.
- Status polling state (`PROCESSING`, `COMPLETED`, `FAILED`).
- In-browser processed video playback.
- ROI metadata side panel with frame/timestamp/bbox/confidence.

## 14) Key files to review

- API routes: [backend/app/api/routes.py](/C:/Users/kkewa/Downloads/SentraVision/backend/app/api/routes.py)
- Worker pipeline task: [backend/app/worker/tasks.py](/C:/Users/kkewa/Downloads/SentraVision/backend/app/worker/tasks.py)
- MediaPipe detector: [backend/app/worker/pipeline/detector.py](/C:/Users/kkewa/Downloads/SentraVision/backend/app/worker/pipeline/detector.py)
- PIL draw + ffmpeg encode: [backend/app/worker/pipeline/renderer.py](/C:/Users/kkewa/Downloads/SentraVision/backend/app/worker/pipeline/renderer.py)
- Compose orchestration: [docker-compose.yml](/C:/Users/kkewa/Downloads/SentraVision/docker-compose.yml)
