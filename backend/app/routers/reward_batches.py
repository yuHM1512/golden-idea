from __future__ import annotations

import json
from datetime import datetime
from html import escape
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import extract
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.idea import Idea, IdeaStatus
from app.models.reward_batch import RewardBatch
from app.models.score import IdeaScore
from app.models.user import User
from app.routers.payments import _render_pdf_via_browser
from app.services.email_notifications import send_reward_batch_summary_emails
from app.time_utils import now_display_tz

router = APIRouter(prefix="/reward-batches", tags=["reward-batches"])

QUARTER_MONTHS: dict[int, tuple[int, int]] = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}


class RewardBatchSpecialRewardInput(BaseModel):
    idea_id: int = Field(..., gt=0)
    reward_multiplier: float = Field(..., gt=0, description="Hệ số khen thưởng riêng cho ý tưởng")


class RewardBatchCreate(BaseModel):
    quarter: int = Field(..., ge=1, le=4)
    year: int = Field(..., ge=2020, le=2100)
    coefficient: float = Field(..., gt=0, description="VND / điểm")
    special_rewards: list[RewardBatchSpecialRewardInput] = Field(default_factory=list)
    employee_code: str


def _require_user(db: Session, employee_code: str) -> User:
    code = (employee_code or "").strip().upper()
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Thiếu employee_code")
    user = db.query(User).filter(User.employee_code.ilike(code)).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User không tồn tại")
    return user


def _ie_score_for_idea(scores: list[IdeaScore]) -> IdeaScore | None:
    ie_scores = [score for score in (scores or []) if score.scorer and score.scorer.role == "ie_manager"]
    if not ie_scores:
        return None
    ie_scores.sort(key=lambda score: score.scored_at or datetime.min, reverse=True)
    return ie_scores[0]


def _reward_score_for_idea(idea: Idea) -> int:
    if idea.council_final_score is not None:
        return int(idea.council_final_score)
    ie_score = _ie_score_for_idea(idea.scores or [])
    return int(ie_score.total_score) if ie_score else 0


def _reward_multiplier_for_idea(idea: Idea) -> float:
    value = getattr(idea, "council_reward_multiplier", None)
    if value is None:
        return 1.0
    return float(value)


def _parse_participants(raw_value, fallback_name: str, fallback_code: str) -> list[dict[str, str]]:
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
                if not full_name:
                    continue
                employee_code = str(item.get("employee_code") or "").strip().upper()
                participants.append({"full_name": full_name, "employee_code": employee_code})

    if not participants and (fallback_name or "").strip():
        participants = [{"full_name": fallback_name.strip(), "employee_code": (fallback_code or "").strip().upper()}]

    return participants


def _build_title(idea: Idea) -> str:
    title = (idea.title or "").strip()
    if title:
        return title[:80] + ("..." if len(title) > 80 else "")
    desc = (idea.description or "").strip()
    if not desc:
        return f"Ý tưởng #{idea.id}"
    return desc[:80] + ("..." if len(desc) > 80 else "")


def _normalize_special_rewards(values: list[RewardBatchSpecialRewardInput] | None) -> list[dict[str, float]]:
    normalized: dict[int, float] = {}
    for item in values or []:
        idea_id = int(item.idea_id)
        reward_multiplier = float(item.reward_multiplier)
        if reward_multiplier <= 0:
            continue
        normalized[idea_id] = reward_multiplier
    return [
        {"idea_id": idea_id, "reward_multiplier": reward_multiplier}
        for idea_id, reward_multiplier in sorted(normalized.items(), key=lambda pair: pair[0])
    ]


def _load_special_rewards(raw_value: str | None) -> list[dict[str, float]]:
    if not raw_value:
        return []
    try:
        parsed = json.loads(raw_value)
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(parsed, list):
        return []

    normalized: list[dict[str, float]] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        try:
            idea_id = int(item.get("idea_id"))
            reward_multiplier = float(item.get("reward_multiplier"))
        except (TypeError, ValueError):
            continue
        if idea_id <= 0 or reward_multiplier <= 0:
            continue
        normalized.append({"idea_id": idea_id, "reward_multiplier": reward_multiplier})
    return normalized


def _special_reward_map(raw_value: str | None) -> dict[int, float]:
    return {int(item["idea_id"]): float(item["reward_multiplier"]) for item in _load_special_rewards(raw_value)}


def _load_eligible_ideas(db: Session, year: int, quarter: int) -> list[Idea]:
    month_start, month_end = QUARTER_MONTHS[int(quarter)]
    return (
        db.query(Idea)
        .options(
            joinedload(Idea.unit),
            joinedload(Idea.scores).joinedload(IdeaScore.scorer),
        )
        .filter(
            Idea.status.in_([IdeaStatus.APPROVED, IdeaStatus.REWARDED]),
            Idea.approved_at.isnot(None),
            extract("year", Idea.approved_at) == int(year),
            extract("month", Idea.approved_at) >= int(month_start),
            extract("month", Idea.approved_at) <= int(month_end),
        )
        .order_by(Idea.approved_at, Idea.id)
        .all()
    )


def _serialize_batch(batch: RewardBatch) -> dict:
    special_rewards = _load_special_rewards(batch.special_coefficients)
    return {
        "id": batch.id,
        "quarter": batch.quarter,
        "year": batch.year,
        "coefficient": batch.coefficient,
        "special_rewards": special_rewards,
        "special_reward_count": len(special_rewards),
        "created_at": batch.created_at,
        "created_by": batch.created_by,
    }


def _serialize_batch_with_summary(db: Session, batch: RewardBatch) -> dict:
    payload = _serialize_batch(batch)
    ideas = _load_eligible_ideas(db, int(batch.year), int(batch.quarter))
    special_rewards = _special_reward_map(batch.special_coefficients)
    total_amount = 0
    for idea in ideas:
        score_value = _reward_score_for_idea(idea)
        reward_multiplier = float(special_rewards.get(idea.id, _reward_multiplier_for_idea(idea)))
        participants = _parse_participants(idea.participants_json, idea.full_name or "", idea.employee_code or "")
        total_amount += sum(round(score_value * float(batch.coefficient) * reward_multiplier) for _ in participants)
    payload["total_ideas"] = len(ideas)
    payload["total_amount"] = total_amount
    return payload


def _format_vnd(value: float | int) -> str:
    return f"{int(round(value or 0)):,}".replace(",", ".")


def _format_score_value(value: float | int) -> str:
    number = float(value or 0)
    if number.is_integer():
        return str(int(number))
    return f"{number:.2f}".rstrip("0").rstrip(".")


def _build_signature_block(title: str) -> str:
    return f"""
      <div class="signature-block">
        <div class="signature-title">{escape(title)}</div>
        <div class="signature-space"></div>
      </div>
    """


def _render_reward_minutes_html(*, batch: RewardBatch, items: list[dict], total_amount: float) -> str:
    now = now_display_tz()
    rows_html = "".join(
        f"""
          <tr>
            <td class="center">{index}</td>
            <td>{escape(str(item.get("full_name") or "—"))}</td>
            <td>{escape(str(item.get("unit_name") or "—"))}</td>
            <td>{escape(str(item.get("employee_code") or "—"))}</td>
            <td>{escape(str(item.get("title") or "—"))}</td>
            <td class="right">{escape(_format_score_value(item.get("ie_score") or 0))}</td>
            <td class="right">{escape(_format_score_value(item.get("reward_multiplier") or 1))}</td>
            <td class="right">{escape(_format_vnd(item.get("amount") or 0))}</td>
          </tr>
        """
        for index, item in enumerate(items, start=1)
    )
    signatures_html = "".join(
        [
            _build_signature_block("ĐẠI DIỆN BAN CẢI TIẾN"),
            _build_signature_block("CHỦ TỊCH HỘI ĐỒNG"),
            _build_signature_block("TỔNG GIÁM ĐỐC"),
        ]
    )
    return f"""<!DOCTYPE html>
<html lang="vi">
  <head>
    <meta charset="utf-8" />
    <style>
      @page {{
        size: A4 landscape;
        margin: 14mm 14mm 18mm 14mm;
      }}
      body {{
        font-family: "Times New Roman", serif;
        color: #111827;
        font-size: 12pt;
        line-height: 1.35;
      }}
      .page {{
        width: 100%;
      }}
      .center {{
        text-align: center;
      }}
      .right {{
        text-align: right;
      }}
      .header-top {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 24px;
        margin-bottom: 14px;
      }}
      .company {{
        text-align: center;
        font-size: 13px;
        font-weight: 700;
        text-transform: uppercase;
      }}
      .nation {{
        text-align: center;
        font-weight: 700;
        text-transform: uppercase;
      }}
      .nation-sub {{
        text-align: center;
        font-weight: 700;
        margin-top: 4px;
      }}
      .title {{
        text-align: center;
        font-size: 17pt;
        font-weight: 700;
        text-transform: uppercase;
        margin: 22px 0 8px;
      }}
      .subtitle {{
        text-align: center;
        margin-bottom: 18px;
      }}
      .meta {{
        margin-bottom: 14px;
      }}
      table {{
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;
      }}
      th, td {{
        border: 1px solid #94a3b8;
        padding: 8px 10px;
        vertical-align: top;
        word-wrap: break-word;
      }}
      th {{
        background: #eef3f8;
        text-align: center;
        font-weight: 700;
      }}
      tfoot td {{
        font-weight: 700;
        background: #f8fafc;
      }}
      .signatures {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 20px;
        margin-top: 26px;
      }}
      .signature-block {{
        text-align: center;
      }}
      .signature-title {{
        font-weight: 700;
        min-height: 38px;
      }}
      .signature-space {{
        height: 88px;
      }}
      .date {{
        text-align: right;
        margin-top: 18px;
      }}
      .company-sub {{
        text-align: center;
        margin-top: 4px;
        font-size: 13px;
        font-weight: 700;
      }}
    </style>
  </head>
  <body>
    <div class="page">
      <div class="header-top">
        <div>
          <div class="company">CÔNG TY CỔ PHẦN DỆT MAY 29/3</div>
          <div class="company-sub">HỘI ĐỒNG XÉT DUYỆT SÁNG KIẾN Ý TƯỞNG VÀNG</div>
        </div>
        <div>
          <div class="nation">CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</div>
          <div class="nation-sub">Độc lập - Tự do - Hạnh phúc</div>
        </div>
      </div>

      <div class="title">Biên bản đề nghị khen thưởng ý tưởng vàng</div>
      <div class="subtitle">Đợt khen thưởng Quý {batch.quarter}/{batch.year}</div>
      <div class="meta">Đơn giá áp dụng: <strong>{escape(_format_vnd(batch.coefficient))} VND/điểm</strong></div>

      <table>
        <thead>
          <tr>
            <th style="width:5%;">STT</th>
            <th style="width:16%;">Họ tên</th>
            <th style="width:12%;">Đơn vị</th>
            <th style="width:10%;">Mã số</th>
            <th style="width:27%;">Tên ý tưởng</th>
            <th style="width:8%;">Điểm xét</th>
            <th style="width:10%;">Hệ số khen thưởng</th>
            <th style="width:12%;">Thành tiền</th>
          </tr>
        </thead>
        <tbody>
          {rows_html}
        </tbody>
        <tfoot>
          <tr>
            <td colspan="7" class="right">Tổng cộng</td>
            <td class="right">{escape(_format_vnd(total_amount))}</td>
          </tr>
        </tfoot>
      </table>

      <div class="date">Ngày {now.strftime("%d")} tháng {now.strftime("%m")} năm {now.strftime("%Y")}</div>
      <div class="signatures">{signatures_html}</div>
    </div>
  </body>
</html>"""


@router.post("/")
def create_reward_batch(payload: RewardBatchCreate, db: Session = Depends(get_db)):
    user = _require_user(db, payload.employee_code)
    if user.role not in {"admin", "ie_manager", "bod_manager"}:
        raise HTTPException(status_code=403, detail="Không có quyền tạo đợt khen thưởng")

    eligible_ideas = _load_eligible_ideas(db, payload.year, payload.quarter)
    eligible_idea_ids = {idea.id for idea in eligible_ideas}
    special_rewards = _normalize_special_rewards(payload.special_rewards)
    invalid_idea_ids = [item["idea_id"] for item in special_rewards if item["idea_id"] not in eligible_idea_ids]
    if invalid_idea_ids:
        joined_ids = ", ".join(str(item) for item in invalid_idea_ids)
        raise HTTPException(status_code=400, detail=f"Ý tưởng nổi trội không thuộc quý/năm đã chọn: {joined_ids}")

    batch = RewardBatch(
        quarter=payload.quarter,
        year=payload.year,
        coefficient=payload.coefficient,
        special_coefficients=json.dumps(special_rewards, ensure_ascii=False) if special_rewards else None,
        created_by=payload.employee_code.strip().upper(),
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    send_reward_batch_summary_emails(
        db,
        batch,
        [idea for idea in eligible_ideas if idea.council_final_score is not None],
        {int(item["idea_id"]): float(item["reward_multiplier"]) for item in special_rewards},
    )
    return _serialize_batch(batch)


@router.get("/")
def list_reward_batches(db: Session = Depends(get_db)):
    batches = db.query(RewardBatch).order_by(RewardBatch.year.desc(), RewardBatch.quarter.desc()).all()
    return [_serialize_batch_with_summary(db, batch) for batch in batches]


@router.get("/candidates")
def get_reward_batch_candidates(
    quarter: int = Query(..., ge=1, le=4),
    year: int = Query(..., ge=2020, le=2100),
    db: Session = Depends(get_db),
):
    ideas = _load_eligible_ideas(db, year, quarter)
    items: list[dict] = []
    for idea in ideas:
        score_value = _reward_score_for_idea(idea)
        participants = _parse_participants(idea.participants_json, idea.full_name or "", idea.employee_code or "")
        items.append(
            {
                "idea_id": idea.id,
                "title": _build_title(idea),
                "description": idea.description or "",
                "unit_name": idea.unit.name if idea.unit else "—",
                "ie_score": score_value,
                "council_is_featured": bool(getattr(idea, "council_is_featured", False)),
                "council_reward_multiplier": _reward_multiplier_for_idea(idea),
                "participant_count": len(participants),
                "employee_codes": [item.get("employee_code") or "" for item in participants if item.get("employee_code")],
                "approved_at": idea.approved_at.isoformat() if idea.approved_at else None,
            }
        )
    return {"items": items}


@router.get("/{batch_id}/report")
def get_batch_report(batch_id: int, db: Session = Depends(get_db)):
    batch = db.query(RewardBatch).filter(RewardBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Đợt khen thưởng không tồn tại")

    ideas = _load_eligible_ideas(db, int(batch.year), int(batch.quarter))
    special_rewards = _special_reward_map(batch.special_coefficients)

    items: list[dict] = []
    for idea in ideas:
        score_value = _reward_score_for_idea(idea)
        reward_multiplier = float(special_rewards.get(idea.id, _reward_multiplier_for_idea(idea)))
        participants = _parse_participants(idea.participants_json, idea.full_name or "", idea.employee_code or "")
        for participant in participants:
            amount = round(score_value * float(batch.coefficient) * reward_multiplier)
            items.append(
                {
                    "idea_id": idea.id,
                    "title": _build_title(idea),
                    "full_name": participant.get("full_name") or "—",
                    "unit_name": idea.unit.name if idea.unit else "—",
                    "employee_code": participant.get("employee_code") or "—",
                    "description": idea.description or "",
                    "ie_score": score_value,
                    "council_is_featured": bool(getattr(idea, "council_is_featured", False)),
                    "council_reward_multiplier": _reward_multiplier_for_idea(idea),
                    "reward_multiplier": reward_multiplier,
                    "amount": amount,
                    "approved_at": idea.approved_at.isoformat() if idea.approved_at else None,
                }
            )

    return {
        "batch": _serialize_batch(batch),
        "items": items,
        "total_amount": sum(item["amount"] for item in items),
    }


@router.get("/{batch_id}/minutes-pdf")
def get_batch_minutes_pdf(
    batch_id: int,
    employee_code: str = Query(...),
    db: Session = Depends(get_db),
):
    user = _require_user(db, employee_code)
    if user.role not in {"admin", "ie_manager", "bod_manager"}:
        raise HTTPException(status_code=403, detail="Không có quyền in biên bản")

    report = get_batch_report(batch_id, db)
    batch = db.query(RewardBatch).filter(RewardBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Đợt khen thưởng không tồn tại")

    items = list(report.get("items") or [])
    if not items:
        raise HTTPException(status_code=400, detail="Đợt này chưa có dữ liệu để in biên bản")

    html = _render_reward_minutes_html(
        batch=batch,
        items=items,
        total_amount=float(report.get("total_amount") or 0),
    )
    output_dir = Path("generated") / "reward_batch_minutes"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"reward_batch_minutes_{batch.id}.pdf"
    _render_pdf_via_browser(html, output_path)
    filename = f"bien-ban-khen-thuong-quy-{batch.quarter}-{batch.year}.pdf"
    return FileResponse(
        output_path,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
