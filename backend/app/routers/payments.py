from __future__ import annotations

import json
import subprocess
import tempfile
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.models.idea import Idea, IdeaStatus
from app.models.payment import PaymentSlip
from app.models.review import IdeaReview, ReviewAction, ReviewLevel
from app.models.user import User

router = APIRouter(prefix="/payments", tags=["payments"])

SLIP_AMOUNT = 50000
BROWSER_CANDIDATES = (
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
)


def _normalize_status(value: Any) -> str:
    if value is None:
        return ""
    return str(value).split(".")[-1]


def _role_name(user: User | None) -> str:
    return (user.role or "").strip() if user else "anonymous"


def _scope_kind(user: User) -> str:
    role = _role_name(user)
    if role in {"dept_manager", "sub_dept_manager"}:
        return "dept"
    if role == "unit_represent":
        return "unit_represent"
    if role == "admin":
        return "admin"
    return "anonymous"


def _can_manage_rewards(user: User) -> bool:
    return _role_name(user) in {"admin", "treasurer"}


def _require_user(db: Session, employee_code: str) -> User:
    code = (employee_code or "").strip().upper()
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Thiếu employee_code")
    user = db.query(User).options(joinedload(User.unit)).filter(User.employee_code.ilike(code)).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User không tồn tại")
    return user


def _parse_participants(raw_value: Any, fallback_name: str, fallback_code: str | None) -> list[dict[str, str]]:
    participants: list[dict[str, str]] = []
    if raw_value:
        try:
            parsed = json.loads(raw_value)
        except (TypeError, json.JSONDecodeError):
            parsed = []
        if isinstance(parsed, list):
            for item in parsed:
                if not isinstance(item, dict):
                    continue
                full_name = str(item.get("full_name") or "").strip()
                employee_code = str(item.get("employee_code") or "").strip().upper()
                if full_name:
                    participants.append({"full_name": full_name, "employee_code": employee_code})

    if not participants and (fallback_name or "").strip():
        names = [name.strip() for name in str(fallback_name).split(";") if name.strip()]
        if names:
            participants = [
                {
                    "full_name": names[0],
                    "employee_code": (fallback_code or "").strip().upper(),
                }
            ]

    return participants


def _participant_display(participants: list[dict[str, str]]) -> tuple[str, str]:
    names = [item["full_name"] for item in participants if item.get("full_name")]
    codes = [item["employee_code"] for item in participants if item.get("employee_code")]
    full_name = " + ".join(names) if names else ""
    employee_code = " + ".join(codes) if codes else ""
    return full_name, employee_code


def _idea_display_title(idea: Idea) -> str:
    # The Idea model in this repo doesn't have a title column; many UIs expect a short label.
    # Derive a stable "title" from the first line/sentence of description.
    raw = (idea.description or "").strip()
    if raw:
        first_line = raw.splitlines()[0].strip()
        if len(first_line) > 90:
            return first_line[:87].rstrip() + "..."
        return first_line
    return f"Ý tưởng #{idea.id}"


def _get_or_create_payment_slip(db: Session, idea: Idea) -> PaymentSlip:
    participants = _parse_participants(idea.participants_json, idea.full_name or "", idea.employee_code)
    full_name, primary_codes = _participant_display(participants)

    slip = idea.payment_slip
    if slip is None:
        slip = PaymentSlip(
            idea_id=idea.id,
            employee_code=primary_codes or (idea.employee_code or "").strip().upper() or "-",
            employee_name=full_name or (idea.full_name or "").strip() or f"Idea {idea.id}",
            amount=SLIP_AMOUNT,
        )
        db.add(slip)
        db.flush()
    else:
        slip.employee_name = full_name or slip.employee_name
        slip.employee_code = primary_codes or slip.employee_code
        slip.amount = SLIP_AMOUNT

    return slip


def _latest_approved_review_name(idea: Idea, level: ReviewLevel) -> str:
    matched = [
        review
        for review in (idea.reviews or [])
        if _normalize_status(review.level) == level.value and _normalize_status(review.action) == ReviewAction.APPROVE.value
    ]
    matched.sort(key=lambda review: review.reviewed_at or datetime.min, reverse=True)
    if not matched:
        return ""
    reviewer = matched[0].reviewer
    return (reviewer.full_name or "").strip() if reviewer else ""


def _format_short_date(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.strftime("%d/%m/%Y")


def _build_signature_block(title: str, signer_name: str) -> str:
    approved_html = (
        '<div class="approved-tick">&#10003; Đã duyệt</div>'
        if signer_name
        else '<div class="approved-tick-empty">&nbsp;</div>'
    )
    signer_html = escape(signer_name) if signer_name else "&nbsp;"
    return f"""
      <div class="signature-col">
        <div class="signature-title">{escape(title)}</div>
        <div class="signature-space"></div>
        {approved_html}
        <div class="signature-name">{signer_html}</div>
      </div>
    """


def _find_browser_executable() -> Path:
    for candidate in BROWSER_CANDIDATES:
        if candidate.exists():
            return candidate
    raise HTTPException(status_code=500, detail="Kh\u00f4ng t\u00ecm th\u1ea5y tr\u00ecnh duy\u1ec7t \u0111\u1ec3 xu\u1ea5t PDF")


def _render_pdf_via_browser(html_content: str, output_path: Path) -> None:
    browser = _find_browser_executable()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as handle:
        handle.write(html_content)
        temp_html = Path(handle.name)

    try:
        cmd = [
            str(browser),
            "--headless",
            "--disable-gpu",
            f"--print-to-pdf={output_path}",
            "--print-to-pdf-no-header",
            temp_html.resolve().as_uri(),
        ]
        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)
        if completed.returncode != 0 or not output_path.exists():
            detail = (completed.stderr or completed.stdout or "").strip()
            raise HTTPException(status_code=500, detail=f"Kh\u00f4ng xu\u1ea5t \u0111\u01b0\u1ee3c PDF: {detail or 'unknown error'}")
    finally:
        temp_html.unlink(missing_ok=True)


def _render_payment_slip_html(
    *,
    full_name: str,
    employee_code: str,
    unit_name: str,
    description: str,
    created_at_text: str,
    printed_at: datetime,
    leadership_name: str,
    tech_name: str,
    dept_name: str,
) -> str:
    amount_text = "50.000 VND"
    printed_day = printed_at.strftime("%d")
    printed_month = printed_at.strftime("%m")
    printed_year = printed_at.strftime("%Y")

    signatures_html = "".join(
        [
            _build_signature_block("Lãnh đạo công ty", leadership_name),
            _build_signature_block("P.KTCN", tech_name),
            _build_signature_block("Trưởng bộ phận", dept_name),
            _build_signature_block("Người nhận tiền", ""),
        ]
    )

    return f"""<!DOCTYPE html>
<html lang="vi">
  <head>
    <meta charset="utf-8" />
    <style>
      @page {{
        size: A4;
        margin: 18mm 18mm 20mm 18mm;
      }}
      body {{
        font-family: "Times New Roman", serif;
        font-size: 14pt;
        color: #111;
        line-height: 1.45;
      }}
      .page {{
        width: 100%;
      }}
      .center {{
        text-align: center;
      }}
      .nation {{
        font-weight: 700;
        text-transform: uppercase;
      }}
      .nation-sub {{
        margin-top: 4px;
        font-weight: 700;
      }}
      .title {{
        margin-top: 26px;
        font-size: 22pt;
        font-weight: 700;
        text-transform: uppercase;
      }}
      .content {{
        margin-top: 26px;
      }}
      .row {{
        margin-bottom: 12px;
      }}
      .label {{
        font-weight: 700;
      }}
      .value {{
        font-weight: 400;
      }}
      .amount-row {{
        display: table;
        width: 100%;
        table-layout: fixed;
      }}
      .amount-cell {{
        display: table-cell;
        vertical-align: top;
      }}
      .amount-cell.right {{
        text-align: right;
      }}
      .amount-cell.right .label {{
        padding-right: 6px;
      }}
      .desc {{
        min-height: 72px;
        white-space: pre-wrap;
        text-align: justify;
      }}
      .city-date {{
        margin-top: 18px;
        text-align: right;
        font-style: italic;
      }}
      .signatures {{
        margin-top: 34px;
        display: table;
        width: 100%;
        table-layout: fixed;
      }}
      .signature-col {{
        display: table-cell;
        width: 25%;
        text-align: center;
        vertical-align: top;
        padding: 0 4px;
      }}
      .signature-title {{
        font-weight: 700;
        font-size: 13pt;
      }}
      .signature-space {{
        height: 70px;
      }}
      .approved-tick {{
        font-size: 10pt;
        color: #0f5a2d;
        font-weight: 700;
        text-align: center;
        margin-bottom: 8px;
      }}
      .approved-tick-empty {{
        height: 20px;
        margin-bottom: 8px;
      }}
      .signature-name {{
        min-height: 18px;
        font-size: 9pt;
        font-weight: 700;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }}
      .inline-gap {{
        margin-left: 18px;
      }}
    </style>
  </head>
  <body>
    <div class="page">
      <div class="center nation">CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</div>
      <div class="center nation-sub">ĐỘC LẬP - TỰ DO - HẠNH PHÚC</div>

      <div class="center title">GIẤY NHẬN TIỀN Ý TƯỞNG VÀNG</div>

      <div class="content">
        <div class="row">
          <span class="label">Tôi tên là:</span>
          <span class="value">{escape(full_name)}</span>
          <span class="label inline-gap">Mã số:</span>
          <span class="value">{escape(employee_code or "—")}</span>
        </div>
<div class="row"><span class="label">Bộ phận:</span> <span class="value">{escape(unit_name or "—")}</span></div>

        <div class="row amount-row">
          <div class="amount-cell"><span class="label">Có nhận tiền:</span> <span class="value">{amount_text}</span></div>
          <div class="amount-cell right"><span class="label">Bằng chữ:</span> <span class="value">Năm mươi ngàn đồng chẵn</span></div>
        </div>

        <div class="row">
          <div class="label">Nội dung ý tưởng vàng:</div>
          <div class="desc">{escape(description)}</div>
        </div>

        <div class="row"><span class="label">Ngày đăng nhập trên hệ thống ý tưởng vàng:</span> <span class="value">{escape(created_at_text)}</span></div>

        <div class="city-date">Đà Nẵng, ngày {printed_day} tháng {printed_month} năm {printed_year}</div>

        <div class="signatures">{signatures_html}</div>
      </div>
    </div>
  </body>
</html>
"""


@router.get("/register-bonuses")
async def list_register_bonuses(
    employee_code: str = Query(...),
    db: Session = Depends(get_db),
):
    user = _require_user(db, employee_code)
    if not _can_manage_rewards(user):
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập module chi thưởng")

    ideas = (
        db.query(Idea)
        .options(
            joinedload(Idea.unit),
            joinedload(Idea.payment_slip).joinedload(PaymentSlip.paid_by_user),
            joinedload(Idea.reviews).joinedload(IdeaReview.reviewer),
        )
        .filter(Idea.status.in_([IdeaStatus.APPROVED, IdeaStatus.REWARDED]))
        .order_by(Idea.submitted_at.desc().nullslast(), Idea.id.desc())
        .all()
    )

    rows: list[dict[str, Any]] = []
    for idea in ideas:
        participants = _parse_participants(idea.participants_json, idea.full_name or "", idea.employee_code)
        full_name, primary_codes = _participant_display(participants)
        slip = idea.payment_slip
        approved_reviews = [
            review
            for review in (idea.reviews or [])
            if _normalize_status(review.level) == ReviewLevel.LEADERSHIP.value
            and _normalize_status(review.action) == ReviewAction.APPROVE.value
        ]
        approved_reviews.sort(key=lambda review: review.reviewed_at or datetime.min, reverse=True)
        approved_at = approved_reviews[0].reviewed_at if approved_reviews else None

        rows.append(
            {
                "idea_id": idea.id,
                "slip_id": slip.id if slip else None,
                "title": _idea_display_title(idea),
                "description": idea.description or "",
                "unit_name": (idea.unit.name if idea.unit else "") or "",
                "employee_name": (slip.employee_name if slip else "") or full_name or (idea.full_name or "").strip(),
                "employee_code": (slip.employee_code if slip else "") or primary_codes or (idea.employee_code or "").strip().upper(),
                "reward_amount": float((slip.amount if slip else None) or SLIP_AMOUNT),
                "status": _normalize_status(idea.status),
                "submitted_at": idea.submitted_at,
                "approved_at": approved_at,
                "is_printed": bool(slip.is_printed) if slip else False,
                "print_date": slip.print_date if slip else None,
                "is_paid": bool(slip.employee_received) if slip else False,
                "paid_at": slip.paid_at if slip else None,
                "paid_by_name": (slip.paid_by_user.full_name or "").strip() if slip and slip.paid_by_user else "",
            }
        )

    return {"items": rows, "total": len(rows)}


@router.post("/register-bonuses/{idea_id}/settle")
async def settle_register_bonus(
    idea_id: int,
    employee_code: str = Query(...),
    paid: bool = Query(...),
    db: Session = Depends(get_db),
):
    user = _require_user(db, employee_code)
    if not _can_manage_rewards(user):
        raise HTTPException(status_code=403, detail="Bạn không có quyền cập nhật chi thưởng")

    idea = (
        db.query(Idea)
        .options(joinedload(Idea.payment_slip))
        .filter(Idea.id == idea_id)
        .first()
    )
    if idea is None:
        raise HTTPException(status_code=404, detail="Ý tưởng không tồn tại")
    if _normalize_status(idea.status) not in {IdeaStatus.APPROVED.value, IdeaStatus.REWARDED.value}:
        raise HTTPException(status_code=400, detail="Phiếu chưa đủ điều kiện nhận thưởng")

    slip = _get_or_create_payment_slip(db, idea)
    if paid and not slip.is_printed:
        raise HTTPException(status_code=400, detail="Phiếu chưa in, chưa thể xác nhận chi thưởng")
    if paid:
        slip.employee_received = True
        slip.paid_at = datetime.now()
        slip.paid_by_user_id = user.id
    else:
        slip.employee_received = False
        slip.paid_at = None
        slip.paid_by_user_id = None

    db.commit()
    db.refresh(slip)
    return {
        "message": "Đã cập nhật trạng thái chi thưởng",
        "idea_id": idea.id,
        "is_paid": bool(slip.employee_received),
        "paid_at": slip.paid_at,
        "paid_by_user_id": slip.paid_by_user_id,
    }


@router.get("/slips/idea/{idea_id}/pdf")
async def print_payment_slip_for_idea(
    idea_id: int,
    employee_code: str = Query(...),
    db: Session = Depends(get_db),
):
    user = _require_user(db, employee_code)
    scope = _scope_kind(user)
    if scope not in {"dept", "unit_represent", "admin"}:
        raise HTTPException(status_code=403, detail="Bạn không có quyền in phiếu nhận tiền")

    idea = (
        db.query(Idea)
        .options(
            joinedload(Idea.unit),
            joinedload(Idea.payment_slip),
            joinedload(Idea.reviews).joinedload(IdeaReview.reviewer),
        )
        .filter(Idea.id == idea_id)
        .first()
    )
    if idea is None:
        raise HTTPException(status_code=404, detail="Ý tưởng không tồn tại")

    if scope in {"dept", "unit_represent"} and idea.unit_id != user.unit_id:
        raise HTTPException(status_code=403, detail="Ý tưởng không thuộc đơn vị của bạn")

    status_value = _normalize_status(idea.status)
    if status_value not in {IdeaStatus.APPROVED.value, IdeaStatus.REWARDED.value}:
        raise HTTPException(status_code=400, detail="Chỉ in phiếu cho ý tưởng đã duyệt đủ 3 cấp")

    slip = _get_or_create_payment_slip(db, idea)
    printed_at = datetime.now()
    slip.printed_by_manager_id = user.id
    slip.print_date = printed_at
    slip.is_printed = True

    if status_value == IdeaStatus.APPROVED.value:
        idea.status = IdeaStatus.REWARDED

    leadership_name = _latest_approved_review_name(idea, ReviewLevel.LEADERSHIP)
    tech_name = _latest_approved_review_name(idea, ReviewLevel.COUNCIL)
    dept_name = _latest_approved_review_name(idea, ReviewLevel.DEPT_HEAD)

    html = _render_payment_slip_html(
        full_name=slip.employee_name,
        employee_code=slip.employee_code,
        unit_name=(idea.unit.name if idea.unit else "") or "",
        description=idea.description or "",
        created_at_text=_format_short_date(idea.submitted_at or idea.created_at),
        printed_at=printed_at,
        leadership_name=leadership_name,
        tech_name=tech_name,
        dept_name=dept_name,
    )

    slips_dir = Path(settings.UPLOAD_DIR) / "slips"
    slips_dir.mkdir(parents=True, exist_ok=True)
    output_path = slips_dir / f"payment_slip_idea_{idea.id}.pdf"
    _render_pdf_via_browser(html, output_path)

    db.commit()

    return FileResponse(
        str(output_path),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{output_path.name}"'},
    )
