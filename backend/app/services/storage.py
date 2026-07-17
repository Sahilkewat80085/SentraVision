"""SentraVision — Storage Services"""
import logging
from pathlib import Path
from typing import Optional

import aiofiles
from fastapi import UploadFile

from app.config import get_settings

logger = logging.getLogger("sentravision.storage")
settings = get_settings()


class FileSizeLimitExceeded(Exception):
    """
    Raised when the uploaded file exceeds the configured max upload size limit.
    """
    pass


async def save_upload(
    file: UploadFile,
    target_filename: str,
    max_size_bytes: Optional[int] = None,
) -> Path:
    """
    Saves an uploaded file asynchronously to the local file system.
    Enforces maximum size checks and performs clean rollback on failures.
    """
    # Ensure the upload destination directory exists
    try:
        settings.upload_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        logger.error("Failed to create upload directory at: %s", settings.upload_dir, exc_info=exc)
        raise

    target_path = settings.upload_dir / target_filename
    logger.info("Saving uploaded file '%s' to '%s'", file.filename, target_path)
    
    size = 0
    try:
        async with aiofiles.open(target_path, "wb") as out:
            # Read in chunks of 1MB
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if max_size_bytes and size > max_size_bytes:
                    logger.warning("Upload rejected: file '%s' exceeded size limit of %d bytes", file.filename, max_size_bytes)
                    raise FileSizeLimitExceeded(f"Upload size limit of {max_size_bytes} bytes exceeded")
                await out.write(chunk)
        logger.info("Successfully saved file '%s' (%d bytes)", file.filename, size)
    except Exception as exc:
        logger.error("Error occurred while saving uploaded file '%s'", file.filename, exc_info=exc)
        if target_path.exists():
            try:
                target_path.unlink()
                logger.info("Cleaned up incomplete file target: %s", target_path)
            except Exception as unlink_exc:
                logger.error("Failed to delete incomplete file target: %s", target_path, exc_info=unlink_exc)
        raise
    finally:
        await file.close()

    return target_path


