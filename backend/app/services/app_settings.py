from __future__ import annotations

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.app_setting import AppSetting


def _normalize_bool(value: object, default: bool = False) -> bool:
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def get_bool_setting(key: str, default: bool = False, db: Session | None = None) -> bool:
    owns_session = db is None
    if owns_session:
        db = SessionLocal()
    try:
        row = db.query(AppSetting).filter(AppSetting.key == key).first()
        return _normalize_bool(row.value if row else None, default=default)
    finally:
        if owns_session:
            db.close()


def set_bool_setting(key: str, value: bool, updated_by: str | None = None, db: Session | None = None) -> bool:
    owns_session = db is None
    if owns_session:
        db = SessionLocal()
    try:
        row = db.query(AppSetting).filter(AppSetting.key == key).first()
        if row is None:
            row = AppSetting(key=key)
            db.add(row)
        row.value = "true" if value else "false"
        row.updated_by = (updated_by or "").strip().upper() or None
        db.flush()
        if owns_session:
            db.commit()
        return value
    except Exception:
        if owns_session:
            db.rollback()
        raise
    finally:
        if owns_session:
            db.close()
