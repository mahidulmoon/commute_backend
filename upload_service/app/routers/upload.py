from fastapi import APIRouter, Depends, UploadFile, File, Form, Query
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db_global
from app.logger import logger
from app.utils.auth_validation import get_current_user
from app.utils.response import success_response, error_response
from app.utils.file_handler import save_upload_file, delete_file_from_disk
from app.models.file_record import UploadFileModel

router = APIRouter()


# ---------------------------------------------------------------------------
# POST /profile-picture  — upload profile picture (image only)
# ---------------------------------------------------------------------------
@router.post("/profile-picture")
async def upload_profile_picture(
    file: UploadFile = File(...),
    request_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    try:
        stored_filename, file_path, file_url, file_size, content_type = await save_upload_file(
            file,
            category="profile_pictures",
            is_image_only=True,
        )

        record = UploadFileModel(
            user_id=request_user["id"],
            original_filename=file.filename or stored_filename,
            stored_filename=stored_filename,
            file_path=file_path,
            file_url=file_url,
            file_size=file_size,
            content_type=content_type,
            category="profile_pictures",
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        logger.info(f"Profile picture uploaded for user_id={request_user['id']}: {file_url}")

        return success_response(
            "Profile picture uploaded successfully.",
            {"file_id": record.id, "file_url": file_url},
            201,
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Profile picture upload error: {e}")
        return error_response(str(e), None, 400)


# ---------------------------------------------------------------------------
# POST /file  — generic single file upload
# ---------------------------------------------------------------------------
@router.post("/file")
async def upload_single_file(
    file: UploadFile = File(...),
    category: str = Form(default="general"),
    request_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    try:
        stored_filename, file_path, file_url, file_size, content_type = await save_upload_file(
            file,
            category=category,
            is_image_only=False,
        )

        record = UploadFileModel(
            user_id=request_user["id"],
            original_filename=file.filename or stored_filename,
            stored_filename=stored_filename,
            file_path=file_path,
            file_url=file_url,
            file_size=file_size,
            content_type=content_type,
            category=category,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        logger.info(f"File uploaded for user_id={request_user['id']}: {file_url}")

        return success_response(
            "File uploaded successfully.",
            jsonable_encoder(record),
            201,
        )

    except Exception as e:
        db.rollback()
        logger.error(f"File upload error: {e}")
        return error_response(str(e), None, 400)


# ---------------------------------------------------------------------------
# POST /multiple  — upload up to 10 files at once
# ---------------------------------------------------------------------------
@router.post("/multiple")
async def upload_multiple_files(
    files: List[UploadFile] = File(...),
    category: str = Form(default="general"),
    request_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    try:
        if len(files) > 10:
            return error_response("You can upload a maximum of 10 files at once.", None, 400)

        uploaded = []
        for file in files:
            stored_filename, file_path, file_url, file_size, content_type = await save_upload_file(
                file,
                category=category,
                is_image_only=False,
            )

            record = UploadFileModel(
                user_id=request_user["id"],
                original_filename=file.filename or stored_filename,
                stored_filename=stored_filename,
                file_path=file_path,
                file_url=file_url,
                file_size=file_size,
                content_type=content_type,
                category=category,
            )
            db.add(record)
            db.flush()  # get id without committing yet
            uploaded.append(jsonable_encoder(record))

        db.commit()

        logger.info(f"Multiple upload: {len(uploaded)} files by user_id={request_user['id']}")

        return success_response(
            f"{len(uploaded)} file(s) uploaded successfully.",
            {"files": uploaded, "total": len(uploaded)},
            201,
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Multiple upload error: {e}")
        return error_response(str(e), None, 400)


# ---------------------------------------------------------------------------
# GET /my-files  — paginated list of the authenticated user's uploads
# ---------------------------------------------------------------------------
@router.get("/my-files")
def get_my_files(
    category: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    request_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    try:
        query = db.query(UploadFileModel).filter(
            UploadFileModel.user_id == request_user["id"],
            UploadFileModel.is_deleted == False,
        )

        if category:
            query = query.filter(UploadFileModel.category == category)

        total = query.count()
        items = (
            query.order_by(UploadFileModel.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return success_response(
            "Files fetched successfully.",
            {
                "items": jsonable_encoder(items),
                "total": total,
                "page": page,
                "page_size": page_size,
            },
            200,
        )

    except Exception as e:
        logger.error(f"Fetch my-files error: {e}")
        return error_response(str(e), None, 400)


# ---------------------------------------------------------------------------
# GET /{file_id}  — get metadata of a specific upload
# ---------------------------------------------------------------------------
@router.get("/{file_id}")
def get_file_info(
    file_id: int,
    request_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    try:
        record = db.query(UploadFileModel).filter(
            UploadFileModel.id == file_id,
            UploadFileModel.is_deleted == False,
        ).first()

        if not record:
            return error_response("File not found.", None, 404)

        # Only owner or admin can view metadata
        if record.user_id != request_user["id"] and request_user.get("type") != "ADMIN":
            return error_response("Access denied.", None, 403)

        return success_response("File info fetched.", jsonable_encoder(record), 200)

    except Exception as e:
        logger.error(f"Get file info error: {e}")
        return error_response(str(e), None, 400)


# ---------------------------------------------------------------------------
# DELETE /{file_id}  — soft-delete + remove from disk
# ---------------------------------------------------------------------------
@router.delete("/{file_id}")
def delete_file(
    file_id: int,
    request_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    try:
        record = db.query(UploadFileModel).filter(
            UploadFileModel.id == file_id,
            UploadFileModel.is_deleted == False,
        ).first()

        if not record:
            return error_response("File not found.", None, 404)

        # Only owner or admin can delete
        if record.user_id != request_user["id"] and request_user.get("type") != "ADMIN":
            return error_response("Access denied.", None, 403)

        # Remove from disk
        deleted_from_disk = delete_file_from_disk(record.file_path)

        # Soft-delete in DB
        record.is_deleted = True
        db.commit()

        logger.info(
            f"File {file_id} deleted by user_id={request_user['id']} "
            f"(disk removed: {deleted_from_disk})"
        )

        return success_response("File deleted successfully.", None, 200)

    except Exception as e:
        db.rollback()
        logger.error(f"Delete file error: {e}")
        return error_response(str(e), None, 400)
