# SentraVision Architecture Documentation

This document describes the high-level system architecture and relational database schema details for the SentraVision project.

## System Flowchart

```mermaid
flowchart TD
    User["User Browser / Client UI"] -->|HTTP/8080| NX["Nginx Reverse Proxy Container"]
    NX -->|Static assets| FE["React (Vite) Frontend Container"]
    NX -->|Proxy requests| API["FastAPI Backend Container"]
    API -->|1. Write metadata| DB[("PostgreSQL Database")]
    API -->|2. Store raw video| FS["Processed Video Storage (/data/processed)"]
    API -->|3. Enqueue job| RQ[("Redis Task Broker")]
    RQ -->|4. Pickup Task| CW["Celery Background Worker"]
    CW -->|5. Processing pipeline| VP["FFmpeg + MediaPipe + Pillow Pipeline"]
    VP -->|6. Record ROI frames| DB
    VP -->|7. Export finished video| FS
    NX -->|Stream video files| FS
```

## Relational Database Schema Model

The PostgreSQL schema models videos and their associated Region of Interest (ROI) face detection details:

```mermaid
erDiagram
    videos ||--o{ roi_frames : "has many (Cascading Delete)"
    videos {
      uuid id PK "Unique identifier for video job"
      string original_filename "Original name of uploaded file"
      string stored_filename "Unique internal filename"
      string processed_filename "Output filename with bounding boxes"
      enum status "Job status (PENDING, PROCESSING, COMPLETED, FAILED)"
      string celery_task_id "ID of the associated Celery task"
      float duration_seconds "Duration of video in seconds"
      float fps "Frame rate of the video"
      int frame_count "Total number of video frames"
      int width "Width resolution in pixels"
      int height "Height resolution in pixels"
      int faces_detected "Number of faces detected"
      float processing_time_seconds "Processing runtime duration"
      text error_message "Traceback message on job failure"
      timestamptz created_at "Timestamp of job submission"
      timestamptz updated_at "Timestamp of status update"
    }
    roi_frames {
      int id PK "Autoincremented primary key"
      uuid video_id FK "Reference to parent video record"
      int frame_number "Zero-indexed frame number"
      float timestamp "Offset timestamp from video start"
      int x "Left edge coordinate in pixels"
      int y "Top edge coordinate in pixels"
      int width "Bounding box width in pixels"
      int height "Bounding box height in pixels"
      float confidence "Detection confidence score [0.0, 1.0]"
      timestamptz created_at "Timestamp of detection"
    }
```

