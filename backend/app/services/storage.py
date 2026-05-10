from pathlib import Path

import aiofiles
from fastapi import UploadFile

from app.config import get_settings

settings = get_settings()


async def save_upload(file: UploadFile, target_filename: str) -> Path:
    target_path = settings.upload_dir / target_filename
    async with aiofiles.open(target_path, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            await out.write(chunk)
    await file.close()
    return target_path
