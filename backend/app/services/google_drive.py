from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from io import IOBase
from pathlib import Path
from typing import Iterator
from urllib.parse import urlencode

from fastapi import HTTPException, status
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

from app.config import settings

DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"
DRIVE_FOLDER_MIME = "application/vnd.google-apps.folder"


@dataclass
class DriveUploadResult:
    file_id: str
    folder_id: str
    web_view_link: str | None
    mime_type: str | None
    size: int | None


@dataclass
class DriveUploadSession:
    session_url: str
    folder_id: str


def _escape_drive_query(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _credentials_file() -> Path:
    raw = (settings.GOOGLE_DRIVE_CREDENTIALS_FILE or "").strip()
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Chưa cấu hình GOOGLE_DRIVE_CREDENTIALS_FILE",
        )

    path = Path(raw)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[2] / path
    path = path.resolve()
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Không tìm thấy file credentials Google Drive: {path}",
        )
    return path


@lru_cache(maxsize=1)
def _drive_credentials():
    return service_account.Credentials.from_service_account_file(
        str(_credentials_file()),
        scopes=[DRIVE_SCOPE],
    )


@lru_cache(maxsize=1)
def _drive_service():
    return build("drive", "v3", credentials=_drive_credentials(), cache_discovery=False)


@lru_cache(maxsize=1)
def _authorized_session():
    return AuthorizedSession(_drive_credentials())


def _root_folder_id() -> str:
    folder_id = (settings.GOOGLE_DRIVE_ROOT_FOLDER_ID or "").strip()
    if not folder_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Chưa cấu hình GOOGLE_DRIVE_ROOT_FOLDER_ID",
        )
    return folder_id


def _find_child_folder_id(parent_id: str, folder_name: str) -> str | None:
    service = _drive_service()
    query = (
        f"'{_escape_drive_query(parent_id)}' in parents and "
        f"name = '{_escape_drive_query(folder_name)}' and "
        f"mimeType = '{DRIVE_FOLDER_MIME}' and trashed = false"
    )
    response = service.files().list(
        q=query,
        fields="files(id,name)",
        pageSize=1,
        includeItemsFromAllDrives=True,
        supportsAllDrives=True,
    ).execute()
    files = response.get("files") or []
    return files[0]["id"] if files else None


def ensure_idea_folder(idea_id: int) -> str:
    folder_name = f"idea-{idea_id}"
    parent_id = _root_folder_id()
    existing_id = _find_child_folder_id(parent_id, folder_name)
    if existing_id:
        return existing_id

    service = _drive_service()
    body = {
        "name": folder_name,
        "mimeType": DRIVE_FOLDER_MIME,
        "parents": [parent_id],
    }
    try:
        created = service.files().create(
            body=body,
            fields="id",
            supportsAllDrives=True,
        ).execute()
        return created["id"]
    except HttpError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Không tạo được thư mục Drive cho ý tưởng: {exc}",
        ) from exc


def list_drive_folder_files(folder_id: str) -> list[dict[str, str | int | list[str] | None]]:
    service = _drive_service()
    query = f"'{_escape_drive_query(folder_id)}' in parents and trashed = false"
    response = service.files().list(
        q=query,
        fields="files(id,name,mimeType,size,webViewLink,parents)",
        includeItemsFromAllDrives=True,
        supportsAllDrives=True,
        pageSize=200,
    ).execute()
    return list(response.get("files") or [])


def upload_attachment_to_drive(
    *,
    idea_id: int,
    original_filename: str,
    file_stream: IOBase,
    mime_type: str,
) -> DriveUploadResult:
    folder_id = ensure_idea_folder(idea_id)
    service = _drive_service()
    media = MediaIoBaseUpload(file_stream, mimetype=mime_type, resumable=True)
    body = {
        "name": original_filename,
        "parents": [folder_id],
    }

    try:
        created = service.files().create(
            body=body,
            media_body=media,
            fields="id,mimeType,size,webViewLink",
            supportsAllDrives=True,
        ).execute()
    except HttpError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Không tải được file lên Google Drive: {exc}",
        ) from exc

    return DriveUploadResult(
        file_id=created["id"],
        folder_id=folder_id,
        web_view_link=created.get("webViewLink"),
        mime_type=created.get("mimeType") or mime_type,
        size=int(created["size"]) if created.get("size") is not None else None,
    )


def create_resumable_upload_session(
    *,
    idea_id: int,
    original_filename: str,
    mime_type: str,
    file_size: int,
) -> DriveUploadSession:
    folder_id = ensure_idea_folder(idea_id)
    session = _authorized_session()
    params = urlencode(
        {
            "uploadType": "resumable",
            "supportsAllDrives": "true",
            "fields": "id,mimeType,size,webViewLink",
        }
    )
    url = f"https://www.googleapis.com/upload/drive/v3/files?{params}"
    response = session.post(
        url,
        headers={
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": mime_type,
            "X-Upload-Content-Length": str(file_size),
        },
        json={
            "name": original_filename,
            "parents": [folder_id],
        },
    )
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Không tạo được phiên upload Google Drive: {response.text}",
        )

    session_url = response.headers.get("Location")
    if not session_url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Google Drive không trả về upload session URL",
        )

    return DriveUploadSession(session_url=session_url, folder_id=folder_id)


def get_drive_file_metadata(file_id: str) -> dict[str, str | int | list[str] | None]:
    service = _drive_service()
    try:
        metadata = service.files().get(
            fileId=file_id,
            fields="id,name,mimeType,size,parents,webViewLink",
            supportsAllDrives=True,
        ).execute()
    except HttpError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không đọc được metadata file trên Google Drive: {exc}",
        ) from exc
    return metadata


def request_drive_file_content(file_id: str, range_header: str | None = None):
    session = _authorized_session()
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&supportsAllDrives=true"
    headers = {}
    if range_header:
        headers["Range"] = range_header

    response = session.get(url, headers=headers, stream=True)
    if response.status_code == 404:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File trên Google Drive không tồn tại")
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Không tải được file từ Google Drive: {response.text}",
        )
    return response


def iter_drive_file_content(file_id: str, chunk_size: int = 1024 * 1024) -> Iterator[bytes]:
    response = request_drive_file_content(file_id)
    try:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                yield chunk
    finally:
        response.close()
