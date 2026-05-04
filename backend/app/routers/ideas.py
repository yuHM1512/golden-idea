import json
import mimetypes
from datetime import datetime
from pathlib import Path
from tempfile import SpooledTemporaryFile
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.attachment import FileAttachment
from app.models.idea import Idea, IdeaStatus
from app.schemas import (
    DirectUploadCompleteRequest,
    DirectUploadSessionRequest,
    DirectUploadSessionResponse,
    IdeaCreate,
    IdeaDetailResponse,
    IdeaListResponse,
    IdeaSubmitResponse,
    IdeaUpdate,
)
from app.services.google_drive import (
    create_resumable_upload_session,
    ensure_idea_folder,
    get_drive_file_metadata,
    iter_drive_file_content,
    list_drive_folder_files,
    request_drive_file_content,
    upload_attachment_to_drive,
)

router = APIRouter(prefix="/ideas", tags=["ideas"])


def _truncate(value: str | None, max_length: int) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value[:max_length] if value else None


def _normalize_participants(idea: IdeaCreate) -> list[dict[str, str]]:
    participants: list[dict[str, str]] = []
    for participant in idea.participants or []:
        full_name = (participant.full_name or "").strip()
        employee_code = (participant.employee_code or "").strip()
        if full_name:
            participants.append({"full_name": full_name, "employee_code": employee_code})

    if not participants:
        full_name = (idea.full_name or "").strip()
        if full_name:
            participants.append({
                "full_name": full_name,
                "employee_code": (idea.employee_code or "").strip(),
            })

    return participants


def build_attachment_file_url(attachment: FileAttachment) -> str:
    provider = (attachment.storage_provider or "").strip().lower()
    if provider == "google_drive" and attachment.external_file_id:
        return f"/api/ideas/attachments/{attachment.id}/content"

    file_path = (attachment.file_path or "").replace("\\", "/").lstrip("/")
    return f"/{file_path}" if file_path else "#"


def _validate_attachment_filename(original_filename: str) -> str:
    suffix = Path(original_filename).suffix.lower().lstrip(".")
    if not suffix:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File không có đuôi mở rộng")

    allowed = {ext.lower().lstrip(".") for ext in (settings.ALLOWED_EXTENSIONS or [])}
    if suffix not in allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Không hỗ trợ định dạng: {suffix}")
    return suffix


def _create_drive_attachment(
    *,
    db: Session,
    idea_id: int,
    original_filename: str,
    file_type: str,
    file_size: int,
    drive_file_id: str,
    folder_id: str | None,
    web_view_link: str | None,
    mime_type: str | None,
) -> FileAttachment:
    attachment = FileAttachment(
        idea_id=idea_id,
        original_filename=original_filename,
        stored_filename=drive_file_id,
        file_type=file_type,
        file_size=file_size,
        file_path=f"drive://{drive_file_id}",
        storage_provider="google_drive",
        external_file_id=drive_file_id,
        external_folder_id=folder_id,
        external_url=web_view_link,
        mime_type=mime_type,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


def sync_idea_attachments_from_drive(db: Session, idea_id: int) -> list[FileAttachment]:
    folder_id = ensure_idea_folder(idea_id)
    drive_files = list_drive_folder_files(folder_id)
    if not drive_files:
        return []

    existing_ids = {
        str(file_id)
        for (file_id,) in db.query(FileAttachment.external_file_id)
        .filter(FileAttachment.idea_id == idea_id, FileAttachment.external_file_id.is_not(None))
        .all()
    }

    created: list[FileAttachment] = []
    for item in drive_files:
        drive_file_id = str(item.get("id") or "").strip()
        original_filename = str(item.get("name") or "").strip()
        if not drive_file_id or not original_filename or drive_file_id in existing_ids:
            continue

        try:
            file_type = _validate_attachment_filename(original_filename)
        except HTTPException:
            continue

        attachment = _create_drive_attachment(
            db=db,
            idea_id=idea_id,
            original_filename=original_filename,
            file_type=file_type,
            file_size=int(item.get("size") or 0),
            drive_file_id=drive_file_id,
            folder_id=folder_id,
            web_view_link=str(item.get("webViewLink") or ""),
            mime_type=str(item.get("mimeType") or "application/octet-stream"),
        )
        created.append(attachment)
        existing_ids.add(drive_file_id)

    return created


@router.post("/", response_model=IdeaSubmitResponse)
async def submit_idea(idea: IdeaCreate, db: Session = Depends(get_db)):
    """
    Submit a new idea (Phiếu đăng ký ý tưởng)
    Captures: full_name, employee_code, phone, bo_phan, position, product_code,
              category, description, is_anonymous, unit_id
    """
    try:
        participants = _normalize_participants(idea)
        if not participants:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vui lòng nhập ít nhất 1 người tham gia",
            )

        display_full_name = "; ".join(participant["full_name"] for participant in participants)
        primary_employee_code = next(
            (participant["employee_code"] for participant in participants if participant["employee_code"]),
            None,
        )

        new_idea = Idea(
            full_name=_truncate(display_full_name, 255),
            employee_code=_truncate(primary_employee_code, 50),
            participants_json=json.dumps(participants, ensure_ascii=False),
            phone_number=idea.phone_number,
            bo_phan=_truncate(idea.bo_phan, 255),
            position=idea.position,
            product_code=idea.product_code,
            category=idea.category,
            description=idea.description,
            is_anonymous=idea.is_anonymous,
            unit_id=idea.unit_id,
            status=IdeaStatus.SUBMITTED,
            submitted_at=datetime.utcnow(),
        )

        db.add(new_idea)
        db.commit()
        db.refresh(new_idea)

        return {
            "id": new_idea.id,
            "status": new_idea.status,
            "submitted_at": new_idea.submitted_at,
            "message": "Ý tưởng của bạn đã được đăng ký thành công",
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi gửi ý tưởng: {exc}",
        )


@router.get("/", response_model=List[IdeaListResponse])
async def list_ideas(
    skip: int = 0,
    limit: int = 100,
    status: str = None,
    unit_id: int = None,
    db: Session = Depends(get_db),
):
    """List ideas with filters"""
    # TODO: Implement filtering
    pass


@router.get("/{idea_id}", response_model=IdeaDetailResponse)
async def get_idea(idea_id: int, db: Session = Depends(get_db)):
    """Get idea details with attachments"""
    # TODO: Implement
    pass


@router.put("/{idea_id}", response_model=IdeaDetailResponse)
async def update_idea(
    idea_id: int,
    idea: IdeaUpdate,
    db: Session = Depends(get_db),
):
    """Update idea (before submission)"""
    # TODO: Implement - only allow if status is DRAFT
    pass


@router.post("/{idea_id}/upload", tags=["attachments"])
async def upload_attachment(
    idea_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload image/video attachment to idea.
    Phase 1 keeps the current UI and stores files on Google Drive.
    """
    idea = db.query(Idea).filter(Idea.id == idea_id).first()
    if idea is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Idea không tồn tại")

    original_filename = (file.filename or "").strip()
    if not original_filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Thiếu tên file")

    suffix = _validate_attachment_filename(original_filename)

    max_bytes = int(settings.MAX_FILE_SIZE_MB) * 1024 * 1024
    size = 0
    mime_type = (file.content_type or "").strip() or mimetypes.guess_type(original_filename)[0] or "application/octet-stream"
    temp_file = SpooledTemporaryFile(max_size=10 * 1024 * 1024, mode="w+b")

    try:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File vượt quá giới hạn {settings.MAX_FILE_SIZE_MB}MB",
                )
            temp_file.write(chunk)

        temp_file.seek(0)
        uploaded = upload_attachment_to_drive(
            idea_id=idea_id,
            original_filename=original_filename,
            file_stream=temp_file,
            mime_type=mime_type,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Lỗi lưu file: {exc}")
    finally:
        temp_file.close()
        await file.close()

    attachment = _create_drive_attachment(
        db=db,
        idea_id=idea_id,
        original_filename=original_filename,
        file_type=suffix,
        file_size=uploaded.size or size,
        drive_file_id=uploaded.file_id,
        folder_id=uploaded.folder_id,
        web_view_link=uploaded.web_view_link,
        mime_type=uploaded.mime_type or mime_type,
    )

    return {
        "id": attachment.id,
        "idea_id": attachment.idea_id,
        "original_filename": attachment.original_filename,
        "file_type": attachment.file_type,
        "file_size": attachment.file_size,
        "file_path": attachment.file_path,
        "file_url": build_attachment_file_url(attachment),
        "uploaded_at": attachment.uploaded_at,
    }


@router.post("/{idea_id}/upload-session", response_model=DirectUploadSessionResponse, tags=["attachments"])
async def create_attachment_upload_session(
    idea_id: int,
    payload: DirectUploadSessionRequest,
    db: Session = Depends(get_db),
):
    idea = db.query(Idea).filter(Idea.id == idea_id).first()
    if idea is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Idea không tồn tại")

    original_filename = (payload.original_filename or "").strip()
    if not original_filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Thiếu tên file")

    _validate_attachment_filename(original_filename)
    if payload.file_size > int(settings.MAX_FILE_SIZE_MB) * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File vượt quá giới hạn {settings.MAX_FILE_SIZE_MB}MB",
        )

    mime_type = (payload.content_type or "").strip() or mimetypes.guess_type(original_filename)[0] or "application/octet-stream"
    session = create_resumable_upload_session(
        idea_id=idea_id,
        original_filename=original_filename,
        mime_type=mime_type,
        file_size=payload.file_size,
    )
    return DirectUploadSessionResponse(session_url=session.session_url, folder_id=session.folder_id)


@router.post("/{idea_id}/attachments/complete", tags=["attachments"])
async def complete_attachment_upload(
    idea_id: int,
    payload: DirectUploadCompleteRequest,
    db: Session = Depends(get_db),
):
    idea = db.query(Idea).filter(Idea.id == idea_id).first()
    if idea is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Idea không tồn tại")

    drive_file_id = (payload.drive_file_id or "").strip()
    original_filename = (payload.original_filename or "").strip()
    if not drive_file_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Thiếu drive_file_id")
    if not original_filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Thiếu tên file")

    suffix = _validate_attachment_filename(original_filename)
    metadata = get_drive_file_metadata(drive_file_id)
    parent_ids = [str(item) for item in (metadata.get("parents") or [])]
    expected_folder_id = ensure_idea_folder(idea_id)
    if not parent_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File Google Drive chưa nằm trong thư mục ý tưởng")
    if expected_folder_id not in parent_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File Google Drive không thuộc đúng thư mục của ý tưởng này")

    existing = (
        db.query(FileAttachment)
        .filter(FileAttachment.idea_id == idea_id, FileAttachment.external_file_id == drive_file_id)
        .first()
    )
    if existing is not None:
        return {
            "id": existing.id,
            "idea_id": existing.idea_id,
            "original_filename": existing.original_filename,
            "file_type": existing.file_type,
            "file_size": existing.file_size,
            "file_path": existing.file_path,
            "file_url": build_attachment_file_url(existing),
            "uploaded_at": existing.uploaded_at,
        }

    attachment = _create_drive_attachment(
        db=db,
        idea_id=idea_id,
        original_filename=original_filename,
        file_type=suffix,
        file_size=int(metadata.get("size") or payload.file_size or 0),
        drive_file_id=drive_file_id,
        folder_id=parent_ids[0],
        web_view_link=str(metadata.get("webViewLink") or ""),
        mime_type=str(metadata.get("mimeType") or payload.content_type or "application/octet-stream"),
    )

    return {
        "id": attachment.id,
        "idea_id": attachment.idea_id,
        "original_filename": attachment.original_filename,
        "file_type": attachment.file_type,
        "file_size": attachment.file_size,
        "file_path": attachment.file_path,
        "file_url": build_attachment_file_url(attachment),
        "uploaded_at": attachment.uploaded_at,
    }


@router.get("/attachments/{attachment_id}/content", tags=["attachments"])
async def get_attachment_content(attachment_id: int, request: Request, db: Session = Depends(get_db)):
    attachment = db.query(FileAttachment).filter(FileAttachment.id == attachment_id).first()
    if attachment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File đính kèm không tồn tại")

    provider = (attachment.storage_provider or "").strip().lower()
    if provider != "google_drive" or not attachment.external_file_id:
        file_path = Path(settings.UPLOAD_DIR) / (attachment.stored_filename or "")
        if not file_path.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy file cục bộ")
        media_type = attachment.mime_type or mimetypes.guess_type(attachment.original_filename)[0] or "application/octet-stream"
        return StreamingResponse(
            file_path.open("rb"),
            media_type=media_type,
        )

    metadata = get_drive_file_metadata(attachment.external_file_id)
    media_type = str(metadata.get("mimeType") or attachment.mime_type or "application/octet-stream")
    range_header = request.headers.get("range")
    upstream = request_drive_file_content(attachment.external_file_id, range_header=range_header)
    headers = {
        "Accept-Ranges": "bytes",
    }
    content_range = upstream.headers.get("Content-Range")
    if content_range:
        headers["Content-Range"] = content_range
    if upstream.status_code == 206:
        content_length = upstream.headers.get("Content-Length")
        if content_length:
            headers["Content-Length"] = content_length

    status_code = 206 if upstream.status_code == 206 or content_range else 200

    def _stream_upstream():
        try:
            for chunk in upstream.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    yield chunk
        finally:
            upstream.close()

    return StreamingResponse(
        _stream_upstream(),
        media_type=media_type,
        headers=headers,
        status_code=status_code,
    )


@router.delete("/{idea_id}/attachments/{attachment_id}")
async def delete_attachment(
    idea_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
):
    """Delete attachment"""
    # TODO: Implement
    pass


@router.post("/{idea_id}/submit", response_model=IdeaSubmitResponse)
async def finalize_submission(idea_id: int, db: Session = Depends(get_db)):
    """Finalize submission (move from DRAFT to SUBMITTED)"""
    # TODO: Implement
    pass


@router.post("/{idea_id}/cancel")
async def cancel_idea(idea_id: int, db: Session = Depends(get_db)):
    """Cancel submitted idea"""
    # TODO: Implement
    pass
