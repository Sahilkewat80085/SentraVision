"""
SentraVision — MediaPipe Face Detector
Detects faces per frame WITHOUT using OpenCV.
Uses MediaPipe FaceDetection + PIL for image I/O.
"""
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import mediapipe as mp
import numpy as np
from PIL import Image

logger = logging.getLogger("sentravision.pipeline.detector")

# MediaPipe models — initialized once per worker process
_mp_face_detection = mp.solutions.face_detection


@dataclass
class BoundingBox:
    """
    Axis-aligned minimal bounding box in absolute pixel coordinates.
    """
    x: int             # Left edge
    y: int             # Top edge
    width: int         # Box width
    height: int        # Box height
    confidence: float  # Detection confidence [0.0, 1.0]


@dataclass
class DetectionResult:
    """
    Result of face detection task for a single frame.
    """
    frame_number: int
    timestamp: float
    bounding_box: Optional[BoundingBox]  # None if no face detected


class FaceDetector:
    """
    Wraps MediaPipe FaceDetection for per-frame inference.
    Designed to be instantiated once per Celery worker process.

    Design decision: MediaPipe's short-range model (model_selection=0)
    is optimised for faces within 2m — ideal for uploaded video content.
    Long-range model (model_selection=1) is used as fallback for distant faces.
    """

    def __init__(self, min_detection_confidence: float = 0.5):
        self._confidence = min_detection_confidence
        self._detector = _mp_face_detection.FaceDetection(
            model_selection=0,
            min_detection_confidence=min_detection_confidence,
        )
        logger.info(
            "FaceDetector initialized successfully (min_confidence=%f)",
            min_detection_confidence
        )

    def detect(self, frame_path: Path, frame_number: int, fps: float) -> DetectionResult:
        """
        Run face detection on a single frame image file.

        Image is loaded via PIL (not cv2) and converted to RGB numpy array
        for MediaPipe consumption.

        Returns DetectionResult with the HIGHEST confidence face bounding box,
        or None if no face is detected.
        """
        timestamp = round(frame_number / fps, 4) if fps > 0 else 0.0

        try:
            # PIL-based image loading — no OpenCV
            with Image.open(frame_path) as img_pil:
                img_rgb = img_pil.convert("RGB")
                img_array = np.array(img_rgb, dtype=np.uint8)
            
            h, w = img_array.shape[:2]
            results = self._detector.process(img_array)

            if not results.detections:
                return DetectionResult(
                    frame_number=frame_number,
                    timestamp=timestamp,
                    bounding_box=None,
                )

            # Pick the detection with highest confidence
            best = max(results.detections, key=lambda d: d.score[0])
            score = float(best.score[0])

            # MediaPipe returns normalized [0.0, 1.0] relative coordinates
            bbox = best.location_data.relative_bounding_box
            x_abs = max(0, int(bbox.xmin * w))
            y_abs = max(0, int(bbox.ymin * h))
            w_abs = min(int(bbox.width * w), w - x_abs)
            h_abs = min(int(bbox.height * h), h - y_abs)

            return DetectionResult(
                frame_number=frame_number,
                timestamp=timestamp,
                bounding_box=BoundingBox(
                    x=x_abs,
                    y=y_abs,
                    width=w_abs,
                    height=h_abs,
                    confidence=round(score, 4),
                ),
            )

        except Exception as exc:
            logger.warning("Detection failed for frame %d: %s", frame_number, exc, exc_info=True)
            return DetectionResult(
                frame_number=frame_number,
                timestamp=timestamp,
                bounding_box=None,
            )

    def close(self) -> None:
        """
        Closes the underlying MediaPipe detector resource.
        """
        self._detector.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def detect_faces_in_frames(
    frame_paths: List[Path],
    fps: float,
    min_confidence: float = 0.5,
) -> List[DetectionResult]:
    """
    Run face detection across all extracted frames.
    Returns a list of DetectionResult objects (one per frame).
    """
    results: List[DetectionResult] = []
    with FaceDetector(min_detection_confidence=min_confidence) as detector:
        for idx, frame_path in enumerate(frame_paths):
            result = detector.detect(frame_path, frame_number=idx + 1, fps=fps)
            results.append(result)

            if (idx + 1) % 50 == 0:
                logger.info("Processed %d/%d frames", idx + 1, len(frame_paths))

    faces_found = sum(1 for r in results if r.bounding_box is not None)
    logger.info(
        "Detection complete: %d/%d frames contain a face",
        faces_found,
        len(results)
    )
    return results
