from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.attachment import FileAttachment
from app.models.idea import Idea
from app.models.labor_second_price import LaborSecondPrice
from app.models.unit import Unit
from app.models.payment import PaymentSlip
from app.models.reward_batch import RewardBatch
from app.models.score import IdeaScore
from app.models.score_revision import IdeaScoreRevision
from app.models.standardized_idea_replication import StandardizedIdeaReplication
from app.models.user import User
from app.schemas import (
    AdminSettingsResponse,
    EmailAutomationUpdateRequest,
    IdeaBulkDeleteRequest,
    IdeaHardDeleteResponse,
    IdeaTaxonomyResponse,
    IdeaTaxonomyUpdateRequest,
    LaborSecondPriceSettingsResponse,
    LaborSecondPriceSettingsUpdateRequest,
)
from app.services.app_settings import get_bool_setting, get_json_setting, set_bool_setting, set_json_setting
from app.services.google_drive import delete_drive_file
from app.services.roles import has_role

router = APIRouter(prefix="/settings", tags=["settings"])

EMAIL_AUTOMATION_KEY = "email_automation_enabled"
IDEA_TAXONOMY_KEY = "idea_taxonomy"
LABOR_SECOND_PRICES_KEY = "labor_second_prices"
DEFAULT_LABOR_SECOND_PRICE = 6.14
DEFAULT_IDEA_CATEGORIES = [
    {"name": "Số hoá", "requires_stage": False},
    {"name": "Quy trình", "requires_stage": True},
    {"name": "Thiết bị", "requires_stage": True},
    {"name": "Phụ trợ", "requires_stage": True},
    {"name": "Chuẩn bị", "requires_stage": True},
    {"name": "Cử gá", "requires_stage": True},
    {"name": "Form", "requires_stage": True},
    {"name": "Thao tác", "requires_stage": True},
]
DEFAULT_IDEA_STAGES = [
    "Chần gòn",
    "Chỉ ly",
    "Túi mổ",
    "Túi đáp",
    "Túi hộp",
    "Túi xéo",
    "Baget",
    "Lưng",
    "Tam giác lai",
    "Bách",
    "Nẹp dơ/Nẹp che",
    "Nắp túi",
    "Măng-sét",
    "Cổ",
    "Đô/Decoup",
    "Mũ",
    "Dây kéo tà",
    "Chắn gió/Thông gió",
    "Yếm",
]


def _require_admin(db: Session, employee_code: str) -> User:
    code = (employee_code or "").strip().upper()
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Thiếu employee_code")
    user = db.query(User).filter(User.employee_code.ilike(code)).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User không tồn tại")
    if not has_role(user, "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Chỉ admin được sử dụng chức năng này")
    return user


def _require_settings_manager(db: Session, employee_code: str) -> User:
    code = (employee_code or "").strip().upper()
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Thiáº¿u employee_code")
    user = db.query(User).filter(User.employee_code.ilike(code)).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User khÃ´ng tá»“n táº¡i")
    if not (has_role(user, "admin") or has_role(user, "ie_manager")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Chá»‰ admin hoáº·c ban cáº£i tiáº¿n Ä‘Æ°á»£c sá»­ dá»¥ng chá»©c nÄƒng nÃ y")
    return user


def _require_labor_second_price_reader(db: Session, employee_code: str) -> User:
    code = (employee_code or "").strip().upper()
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Thieu employee_code")
    user = db.query(User).filter(User.employee_code.ilike(code)).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User khong ton tai")
    if not any(has_role(user, role) for role in {"admin", "ie_manager", "digital_manager", "dept_manager", "sub_dept_manager", "bod_manager"}):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Khong co quyen xem don gia giay CN")
    return user


def _normalize_idea_taxonomy(raw_value: object | None = None) -> IdeaTaxonomyResponse:
    payload = raw_value if isinstance(raw_value, dict) else {}
    raw_categories = payload.get("categories") if isinstance(payload, dict) else None
    raw_stages = payload.get("stages") if isinstance(payload, dict) else None

    def _category_name_from_string(value: object) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        match = re.match(r"^name=(['\"])(?P<name>.*?)\1(?:\s|$)", text)
        return (match.group("name") if match else text).strip()

    def _category_requires_stage_from_string(value: object, name: str) -> bool:
        text = str(value or "").strip()
        match = re.search(r"requires_stage=(?P<value>True|False|true|false|1|0)", text)
        if match:
            return match.group("value").casefold() in {"true", "1"}
        return name.casefold() != "số hoá".casefold()

    def _normalize_category_items(items: object, fallback: list[dict[str, object]]) -> list[dict[str, object]]:
        source = items if isinstance(items, list) else fallback
        result: list[dict[str, object]] = []
        seen: set[str] = set()
        for item in source:
            if isinstance(item, dict):
                name = str(item.get("name") or "").strip()
                requires_stage = bool(item.get("requires_stage", True))
            elif hasattr(item, "name"):
                name = str(getattr(item, "name", "") or "").strip()
                requires_stage = bool(getattr(item, "requires_stage", True))
            else:
                name = _category_name_from_string(item)
                requires_stage = _category_requires_stage_from_string(item, name)
            if not name:
                continue
            lowered = name.casefold()
            if lowered in seen:
                continue
            seen.add(lowered)
            result.append({"name": name, "requires_stage": requires_stage})
        return result or fallback[:]

    def _normalize_items(items: object, fallback: list[str]) -> list[str]:
        source = items if isinstance(items, list) else fallback
        result: list[str] = []
        seen: set[str] = set()
        for item in source:
            text = str(item or "").strip()
            if not text:
                continue
            lowered = text.casefold()
            if lowered in seen:
                continue
            seen.add(lowered)
            result.append(text)
        return result or fallback[:]

    return IdeaTaxonomyResponse(
        categories=_normalize_category_items(raw_categories, DEFAULT_IDEA_CATEGORIES),
        stages=_normalize_items(raw_stages, DEFAULT_IDEA_STAGES),
    )


def _get_idea_taxonomy(db: Session) -> IdeaTaxonomyResponse:
    return _normalize_idea_taxonomy(get_json_setting(IDEA_TAXONOMY_KEY, default=None, db=db))


def _normalize_labor_second_prices(raw_value: object | None = None) -> LaborSecondPriceSettingsResponse:
    source = raw_value if isinstance(raw_value, list) else []
    normalized: dict[int, float] = {}
    for item in source:
        if not isinstance(item, dict):
            continue
        try:
            year = int(item.get("year"))
            labor_second_price = float(item.get("labor_second_price"))
        except (TypeError, ValueError):
            continue
        if year < 2000 or year > 2100:
            continue
        if labor_second_price < 0:
            continue
        normalized[year] = labor_second_price
    return LaborSecondPriceSettingsResponse(
        items=[
            {"year": year, "labor_second_price": normalized[year]}
            for year in sorted(normalized.keys(), reverse=True)
        ]
    )


def _get_labor_second_prices(db: Session) -> LaborSecondPriceSettingsResponse:
    rows = db.query(LaborSecondPrice).order_by(LaborSecondPrice.year.desc()).all()
    if rows:
        return LaborSecondPriceSettingsResponse(
            items=[
                {"year": row.year, "labor_second_price": row.labor_second_price}
                for row in rows
            ]
        )
    return _normalize_labor_second_prices(get_json_setting(LABOR_SECOND_PRICES_KEY, default=None, db=db))


def _cleanup_reward_batch_refs(db: Session, idea_id: int) -> int:
    updated = 0
    batches = db.query(RewardBatch).filter(RewardBatch.special_coefficients.is_not(None)).all()
    for batch in batches:
        raw_items = []
        try:
            raw_items = json.loads(batch.special_coefficients or "[]")
        except (TypeError, json.JSONDecodeError):
            raw_items = []
        if not isinstance(raw_items, list):
            raw_items = []
        filtered = [item for item in raw_items if int(item.get("idea_id") or 0) != int(idea_id)]
        if len(filtered) == len(raw_items):
            continue
        batch.special_coefficients = json.dumps(filtered, ensure_ascii=False) if filtered else None
        db.add(batch)
        updated += 1
    return updated


def _delete_attachment_files(attachments: list[FileAttachment]) -> tuple[int, int, list[str]]:
    removed_google_drive_files = 0
    removed_local_files = 0
    warnings: list[str] = []

    for attachment in attachments:
        provider = (attachment.storage_provider or "").strip().lower()
        if provider == "google_drive" and attachment.external_file_id:
            try:
                delete_drive_file(attachment.external_file_id)
                removed_google_drive_files += 1
            except HTTPException as exc:
                warnings.append(f"Google Drive file {attachment.external_file_id}: {exc.detail}")
            except Exception as exc:
                warnings.append(f"Google Drive file {attachment.external_file_id}: {exc}")
            continue

        file_path = Path(attachment.file_path or "")
        if not file_path.is_absolute():
            file_path = Path(__file__).resolve().parents[2] / file_path
        try:
            if file_path.is_file():
                file_path.unlink()
                removed_local_files += 1
        except Exception as exc:
            warnings.append(f"Local file {file_path}: {exc}")

    return removed_google_drive_files, removed_local_files, warnings


def _delete_single_idea(db: Session, idea: Idea) -> IdeaHardDeleteResponse:
    idea_id = int(idea.id)
    attachments = list(idea.attachments or [])
    removed_reward_batch_refs = 0
    try:
        removed_reward_batch_refs = _cleanup_reward_batch_refs(db, idea_id)
        db.query(IdeaScoreRevision).filter(IdeaScoreRevision.idea_id == idea_id).delete(synchronize_session=False)
        db.query(StandardizedIdeaReplication).filter(StandardizedIdeaReplication.idea_id == idea_id).delete(synchronize_session=False)
        db.query(PaymentSlip).filter(PaymentSlip.idea_id == idea_id).delete(synchronize_session=False)
        db.query(IdeaScore).filter(IdeaScore.idea_id == idea_id).delete(synchronize_session=False)
        db.delete(idea)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Không xóa được ý tưởng: {exc}")

    removed_google_drive_files, removed_local_files, cleanup_warnings = _delete_attachment_files(attachments)
    return IdeaHardDeleteResponse(
        idea_id=idea_id,
        deleted=True,
        removed_reward_batch_refs=removed_reward_batch_refs,
        removed_google_drive_files=removed_google_drive_files,
        removed_local_files=removed_local_files,
        cleanup_warnings=cleanup_warnings,
    )


@router.get("/admin", response_model=AdminSettingsResponse)
async def get_admin_settings(employee_code: str = Query(...), db: Session = Depends(get_db)):
    _require_admin(db, employee_code)
    return AdminSettingsResponse(
        email_automation_enabled=get_bool_setting(EMAIL_AUTOMATION_KEY, default=False, db=db),
        idea_taxonomy=_get_idea_taxonomy(db),
    )


@router.put("/admin/email-automation", response_model=AdminSettingsResponse)
async def update_email_automation(payload: EmailAutomationUpdateRequest, db: Session = Depends(get_db)):
    user = _require_admin(db, payload.employee_code)
    enabled = set_bool_setting(EMAIL_AUTOMATION_KEY, payload.enabled, updated_by=user.employee_code, db=db)
    db.commit()
    return AdminSettingsResponse(
        email_automation_enabled=enabled,
        idea_taxonomy=_get_idea_taxonomy(db),
    )


@router.get("/idea-taxonomy", response_model=IdeaTaxonomyResponse)
async def get_idea_taxonomy(db: Session = Depends(get_db)):
    return _get_idea_taxonomy(db)


@router.get("/labor-second-prices", response_model=LaborSecondPriceSettingsResponse)
async def get_labor_second_prices(employee_code: str = Query(...), db: Session = Depends(get_db)):
    _require_labor_second_price_reader(db, employee_code)
    return _get_labor_second_prices(db)


@router.put("/labor-second-prices", response_model=LaborSecondPriceSettingsResponse)
async def update_labor_second_prices(payload: LaborSecondPriceSettingsUpdateRequest, db: Session = Depends(get_db)):
    user = _require_settings_manager(db, payload.employee_code)
    normalized = _normalize_labor_second_prices(
        [{"year": item.year, "labor_second_price": item.labor_second_price} for item in payload.items]
    )
    wanted_years = {item.year for item in normalized.items}
    if wanted_years:
        db.query(LaborSecondPrice).filter(~LaborSecondPrice.year.in_(wanted_years)).delete(synchronize_session=False)
    else:
        db.query(LaborSecondPrice).delete(synchronize_session=False)
    for item in normalized.items:
        row = db.query(LaborSecondPrice).filter(LaborSecondPrice.year == item.year).first()
        if row is None:
            row = LaborSecondPrice(year=item.year)
            db.add(row)
        row.labor_second_price = item.labor_second_price
        row.updated_by = user.employee_code
    db.commit()
    return normalized


@router.put("/admin/idea-taxonomy", response_model=IdeaTaxonomyResponse)
async def update_idea_taxonomy(payload: IdeaTaxonomyUpdateRequest, db: Session = Depends(get_db)):
    user = _require_admin(db, payload.employee_code)
    normalized = _normalize_idea_taxonomy(
        {
            "categories": payload.categories,
            "stages": payload.stages,
        }
    )
    set_json_setting(
        IDEA_TAXONOMY_KEY,
        {
            "categories": [
                {
                    "name": item.name,
                    "requires_stage": bool(item.requires_stage),
                }
                for item in normalized.categories
            ],
            "stages": normalized.stages,
        },
        updated_by=user.employee_code,
        db=db,
    )
    db.commit()
    return normalized


@router.get("/admin/ideas")
async def list_admin_ideas(employee_code: str = Query(...), db: Session = Depends(get_db)):
    _require_admin(db, employee_code)
    ideas = (
        db.query(Idea)
        .outerjoin(Unit, Unit.id == Idea.unit_id)
        .options(joinedload(Idea.unit))
        .order_by(Idea.submitted_at.desc(), Idea.id.desc())
        .all()
    )
    items = [
        {
            "id": idea.id,
            "title": idea.title,
            "full_name": idea.full_name,
            "employee_code": idea.employee_code,
            "unit_name": idea.unit.name if idea.unit else "",
            "status": str(idea.status).split(".")[-1] if idea.status is not None else "",
            "category": idea.category,
            "submitted_at": idea.submitted_at.isoformat() if idea.submitted_at else None,
            "description": idea.description or "",
        }
        for idea in ideas
    ]
    return {"items": items, "total": len(items)}


@router.delete("/admin/ideas/{idea_id}", response_model=IdeaHardDeleteResponse)
async def hard_delete_idea(idea_id: int, employee_code: str = Query(...), db: Session = Depends(get_db)):
    _require_admin(db, employee_code)

    idea = (
        db.query(Idea)
        .options(joinedload(Idea.attachments))
        .filter(Idea.id == idea_id)
        .first()
    )
    if idea is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ý tưởng không tồn tại")

    return _delete_single_idea(db, idea)


@router.delete("/admin/ideas")
async def hard_delete_all_ideas(employee_code: str = Query(...), db: Session = Depends(get_db)):
    _require_admin(db, employee_code)
    ideas = (
        db.query(Idea)
        .options(joinedload(Idea.attachments))
        .order_by(Idea.id.asc())
        .all()
    )
    results: list[IdeaHardDeleteResponse] = []
    for idea in ideas:
        results.append(_delete_single_idea(db, idea))

    total_google = sum(item.removed_google_drive_files for item in results)
    total_local = sum(item.removed_local_files for item in results)
    total_reward_refs = sum(item.removed_reward_batch_refs for item in results)
    warnings: list[str] = []
    for item in results:
        warnings.extend(item.cleanup_warnings)

    return {
        "deleted_count": len(results),
        "removed_google_drive_files": total_google,
        "removed_local_files": total_local,
        "removed_reward_batch_refs": total_reward_refs,
        "cleanup_warnings": warnings,
    }


@router.post("/admin/ideas/bulk-delete")
async def hard_delete_selected_ideas(payload: IdeaBulkDeleteRequest, db: Session = Depends(get_db)):
    _require_admin(db, payload.employee_code)
    normalized_ids = sorted({int(item) for item in (payload.idea_ids or []) if int(item) > 0})
    if not normalized_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Danh sách idea_ids đang trống")

    ideas = (
        db.query(Idea)
        .options(joinedload(Idea.attachments))
        .filter(Idea.id.in_(normalized_ids))
        .order_by(Idea.id.asc())
        .all()
    )
    found_ids = {int(item.id) for item in ideas}
    missing_ids = [item for item in normalized_ids if item not in found_ids]

    results: list[IdeaHardDeleteResponse] = []
    for idea in ideas:
        results.append(_delete_single_idea(db, idea))

    total_google = sum(item.removed_google_drive_files for item in results)
    total_local = sum(item.removed_local_files for item in results)
    total_reward_refs = sum(item.removed_reward_batch_refs for item in results)
    warnings: list[str] = []
    for item in results:
        warnings.extend(item.cleanup_warnings)

    return {
        "deleted_count": len(results),
        "deleted_ids": [item.idea_id for item in results],
        "missing_ids": missing_ids,
        "removed_google_drive_files": total_google,
        "removed_local_files": total_local,
        "removed_reward_batch_refs": total_reward_refs,
        "cleanup_warnings": warnings,
    }
