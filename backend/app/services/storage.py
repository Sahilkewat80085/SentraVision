from pathlib import Path

import aiofiles
from fastapi import UploadFile

from app.config import get_settings

settings = get_settings()


class FileSizeLimitExceeded(Exception):
    pass


async def save_upload(file: UploadFile, target_filename: str, max_size_bytes: int = None) -> Path:
    target_path = settings.upload_dir / target_filename
    size = 0
    try:
        async with aiofiles.open(target_path, "wb") as out:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if max_size_bytes and size > max_size_bytes:
                    raise FileSizeLimitExceeded("Upload size limit exceeded")
                await out.write(chunk)
    except Exception:
        if target_path.exists():
            target_path.unlink()
        raise
    finally:
        await file.close()
    return target_path

