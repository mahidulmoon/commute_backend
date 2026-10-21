import os
import re
import uuid
import aiofiles
from datetime import datetime
from typing import Tuple, Set
from fastapi import UploadFile, HTTPException
from app.logger import logger

BASE_URL = os.getenv("BASE_URL", "http://192.168.0.100:8086").rstrip("/")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "25"))
MAX_IMAGE_SIZE_MB = int(os.getenv("MAX_IMAGE_SIZE_MB", "10"))

ALLOWED_IMAGE_EXTENSIONS: Set[str] = {"jpg", "jpeg", "png", "webp", "gif"}
ALLOWED_DOCUMENT_EXTENSIONS: Set[str] = {"pdf", "doc", "docx", "txt", "csv", "xlsx"}
ALLOWED_ALL_EXTENSIONS: Set[str] = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_DOCUMENT_EXTENSIONS


def get_file_extension(filename: str) -> str:
    parts = filename.rsplit(".", 1)
    return parts[1].lower() if len(parts) > 1 else ""


def sanitize_filename(filename: str) -> str:
    # Remove path traversal and illegal characters
    cleaned = re.sub(r"[^\w\.-]", "_", os.path.basename(filename))
    return cleaned[:100]


def validate_image_file(file: UploadFile):
    ext = get_file_extension(file.filename or "")
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image format '.{ext}'. Allowed formats: {sorted(ALLOWED_IMAGE_EXTENSIONS)}"
        )


def validate_general_file(file: UploadFile):
    ext = get_file_extension(file.filename or "")
    if ext not in ALLOWED_ALL_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Disallowed file format '.{ext}'. Allowed formats: {sorted(ALLOWED_ALL_EXTENSIONS)}"
        )


async def save_upload_file(
    file: UploadFile,
    category: str = "general",
    is_image_only: bool = False,
) -> Tuple[str, str, str, int, str]:
    """
    Saves an UploadFile to disk securely partitioned by category and date.
    Returns: (stored_filename, relative_path, file_url, file_size, content_type)
    """
    if is_image_only:
        validate_image_file(file)
    else:
        validate_general_file(file)

    original_filename = sanitize_filename(file.filename or "file")
    ext = get_file_extension(original_filename)
    unique_id = uuid.uuid4().hex
    stored_filename = f"{unique_id}.{ext}" if ext else unique_id

    # Partition by category and current date: uploads/profile_pictures/2026-10-21/uuid.jpg
    date_folder = datetime.utcnow().strftime("%Y-%m-%d")
    clean_category = re.sub(r"[^\w-]", "_", category.lower())
    relative_dir = os.path.join(UPLOAD_DIR, clean_category, date_folder)
    os.makedirs(relative_dir, exist_ok=True)

    file_path = os.path.join(relative_dir, stored_filename)

    max_size_bytes = (MAX_IMAGE_SIZE_MB if is_image_only else MAX_FILE_SIZE_MB) * 1024 * 1024
    file_size = 0

    try:
        async with aiofiles.open(file_path, "wb") as out_file:
            while chunk := await file.read(1024 * 64):  # 64KB chunks
                file_size += len(chunk)
                if file_size > max_size_bytes:
                    limit_mb = MAX_IMAGE_SIZE_MB if is_image_only else MAX_FILE_SIZE_MB
                    raise HTTPException(
                        status_code=400,
                        detail=f"File exceeds maximum allowed size of {limit_mb} MB."
                    )
                await out_file.write(chunk)
    except HTTPException:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.error(f"Error writing file to disk: {e}")
        raise HTTPException(status_code=500, detail="Failed to save file to disk.")
    finally:
        await file.seek(0)

    # Normalize forward slashes for URLs
    url_path = file_path.replace("\\", "/")
    if not url_path.startswith("/"):
        url_path = "/" + url_path

    file_url = f"{BASE_URL}{url_path}"
    content_type = file.content_type or f"application/{ext}"

    logger.info(f"File saved successfully: {file_path} ({file_size} bytes)")
    return stored_filename, file_path, file_url, file_size, content_type


def delete_file_from_disk(file_path: str) -> bool:
    try:
        if os.path.exists(file_path) and os.path.isfile(file_path):
            os.remove(file_path)
            logger.info(f"File removed from disk: {file_path}")
            return True
        return False
    except Exception as e:
        logger.warning(f"Error deleting file {file_path}: {e}")
        return False
