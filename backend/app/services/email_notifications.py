from __future__ import annotations

import json
import smtplib
import ssl
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from html import escape
from typing import Iterable

from sqlalchemy.orm import Session

from app.config import settings
from app.models.idea import Idea
from app.models.reward_batch import RewardBatch
from app.models.review import ReviewLevel
from app.models.score import IdeaScore, K2Type, K3MeasureType
from app.models.score_criteria import ScoreCriteria
from app.models.user import User, UserRole


EMAIL_FOOTER_HTML = """
  <p style="color:#d10000;font-weight:600;margin:20px 0 16px;">
    LƯU Ý: Email này được gửi tự động từ hệ thống, vui lòng không phản hồi trực tiếp qua email này.
    Nếu có thắc mắc hoặc cần hỗ trợ thêm, vui lòng liên hệ trực tiếp nhóm Kiểm soát Hệ thống
    (Phòng Tổng hợp) để được giải đáp.
  </p>
  <p style="margin:0 0 16px;">Trân trọng,</p>
  <div style="color:#0f2f7f;font-weight:700;line-height:1.7;">
    <div>MARCH 29 TEXTILE - GARMENT JOINT STOCK COMPANY</div>
    <div>Email: hachiba@hachibavn.com</div>
    <div>Phone: 0236 3756 999</div>
    <div>Website: hachiba.com.vn</div>
    <div>Address: 60 Me Nhu, Da Nang</div>
  </div>
"""

EMAIL_FOOTER_TEXT = (
    "LƯU Ý: Email này được gửi tự động từ hệ thống, vui lòng không phản hồi trực tiếp qua email này. "
    "Nếu có thắc mắc hoặc cần hỗ trợ thêm, vui lòng liên hệ trực tiếp nhóm Kiểm soát Hệ thống "
    "(Phòng Tổng hợp) để được giải đáp.\n\n"
    "Trân trọng,\n\n"
    "MARCH 29 TEXTILE - GARMENT JOINT STOCK COMPANY\n"
    "Email: hachiba@hachibavn.com\n"
    "Phone: 0236 3756 999\n"
    "Website: hachiba.com.vn\n"
    "Address: 60 Me Nhu, Da Nang"
)

IE_RESULT_BCT_REJECTED = "BCT_REJECTED"
IE_RESULT_UNIT_REVIEW = "UNIT_REVIEW"
IE_RESULT_APPROVED_NO_STANDARDIZATION = "APPROVED_NO_STANDARDIZATION"
IE_RESULT_APPROVED_STANDARDIZATION = "APPROVED_STANDARDIZATION"

IE_RESULT_LABELS = {
    IE_RESULT_BCT_REJECTED: "BCT không duyệt",
    IE_RESULT_UNIT_REVIEW: "XN xét duyệt",
    IE_RESULT_APPROVED_NO_STANDARDIZATION: "Đạt - Không đưa vào chuẩn hoá",
    IE_RESULT_APPROVED_STANDARDIZATION: "Đạt - Đưa vào chuẩn hoá",
}

IE_RESULT_MESSAGES = {
    IE_RESULT_BCT_REJECTED: (
        "Rất tiếc, ý tưởng của đơn vị bạn không được Ban cải tiến phê duyệt. "
        "Đừng bỏ cuộc, hãy tiếp tục nỗ lực để sáng tạo thêm các ý tưởng khác nhé!"
    ),
    IE_RESULT_UNIT_REVIEW: (
        "Ý tưởng của đơn vị bạn đã đủ tiêu chí để nhận thưởng đăng ký nhưng không được tiếp tục "
        "đưa ra Hội đồng sáng kiến để tiếp tục xét. Đề nghị đơn vị tự khen thưởng riêng (nếu có) "
        "và theo dõi phê duyệt từ lãnh đạo để in phiếu nhận thưởng đăng ký."
    ),
    IE_RESULT_APPROVED_NO_STANDARDIZATION: (
        "Ý tưởng của đơn vị bạn đã đủ tiêu chí nhận thưởng đăng ký và được đưa ra Hội đồng sáng kiến "
        "để tiếp tục xét. Đề nghị đơn vị theo dõi phê duyệt từ lãnh đạo để in phiếu nhận thưởng "
        "và chờ đón điểm xét thưởng chính thức tại cuối quý."
    ),
    IE_RESULT_APPROVED_STANDARDIZATION: (
        "Ý tưởng của đơn vị bạn đã đủ tiêu chí nhận thưởng đăng ký và được đưa ra Hội đồng sáng kiến "
        "để tiếp tục xét. Đề nghị đơn vị theo dõi phê duyệt từ lãnh đạo để in phiếu nhận thưởng "
        "và chờ đón điểm xét thưởng chính thức tại cuối quý."
    ),
}

K2_TYPE_LABELS = {
    K2Type.EASY.value: "Dễ áp dụng",
    K2Type.HARD.value: "Khó áp dụng",
    K2Type.NORMAL_EASY.value: "Dễ áp dụng",
    K2Type.NORMAL_HARD.value: "Khó áp dụng",
    K2Type.DIGITAL_SELF_DEVELOPED.value: "Tự phát triển",
    K2Type.DIGITAL_CO_DEVELOPED.value: "Phối hợp phát triển",
    K2Type.DIGITAL_OUTSOURCE.value: "Thuê ngoài",
}

K3_MEASURE_LABELS = {
    K3MeasureType.TIME_SAVED.value: "Đo lường được - Tiết kiệm thời gian",
    K3MeasureType.COST_SAVED.value: "Đo lường được - Tiết kiệm chi phí",
    K3MeasureType.UNMEASURABLE.value: "Không đo lường được",
}

K1_FALLBACK_LABELS = {
    "A1": "Hoàn toàn mới",
    "A2": "Cải tiến từ cái cũ",
    "A3": "Ý tưởng cũ",
}


@dataclass
class ApprovalEmailContext:
    recipients: list[str]
    greeting_name: str
    subject: str
    content_line: str
    idea: Idea
    action_url: str | None = None
    action_text: str | None = None
    extra_html: str = ""
    extra_text: str = ""
    show_idea_table: bool = True


def _email_enabled() -> bool:
    host, username, password, from_email = _smtp_runtime_config()
    return bool(host and username and password and from_email)


def _smtp_runtime_config() -> tuple[str, str, str, str]:
    username = (settings.SMTP_USERNAME or settings.SMTP_EMAIL or "").strip()
    password = (settings.SMTP_PASSWORD or settings.SMTP_APP_PASSWORD or "").strip()
    from_email = (settings.SMTP_FROM_EMAIL or username).strip()
    host = (settings.SMTP_HOST or ("smtp.gmail.com" if username else "")).strip()
    return host, username, password, from_email


def _normalize_emails(values: Iterable[str | None]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        email = (value or "").strip()
        if not email:
            continue
        lowered = email.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        result.append(email)
    return result


def _query_role_recipients(db: Session, role: str) -> list[str]:
    users = (
        db.query(User.email)
        .filter(
            User.role == role,
            User.is_active.is_(True),
            User.email.is_not(None),
        )
        .all()
    )
    return _normalize_emails(email for (email,) in users)


def _query_dept_manager_recipients(db: Session, idea: Idea) -> list[str]:
    emails: list[str] = []
    unit = idea.unit
    if unit and unit.manager and unit.manager.is_active and unit.manager.email:
        emails.append(unit.manager.email)

    if not emails:
        rows = (
            db.query(User.email)
            .filter(
                User.role == UserRole.DEPT_MANAGER.value,
                User.unit_id == idea.unit_id,
                User.is_active.is_(True),
                User.email.is_not(None),
            )
            .all()
        )
        emails.extend(email for (email,) in rows)

    return _normalize_emails(emails)


def _query_unit_leadership_recipients(db: Session, idea: Idea) -> list[str]:
    emails: list[str] = []
    unit = idea.unit
    if unit and unit.manager and unit.manager.is_active and unit.manager.email:
        emails.append(unit.manager.email)

    rows = (
        db.query(User.email)
        .filter(
            User.unit_id == idea.unit_id,
            User.role.in_([UserRole.DEPT_MANAGER.value, UserRole.SUB_DEPT_MANAGER.value]),
            User.is_active.is_(True),
            User.email.is_not(None),
        )
        .all()
    )
    emails.extend(email for (email,) in rows)
    return _normalize_emails(emails)


def _format_submitted_at(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.strftime("%d/%m/%Y %H:%M")


def _table_html(idea: Idea) -> str:
    return f"""
      <table style="border-collapse:collapse;width:100%;margin:18px 0 20px;">
        <thead>
          <tr style="background:#0f2f7f;color:#ffffff;">
            <th style="border:1px solid #9ca3af;padding:10px;text-align:left;">Tên ý tưởng</th>
            <th style="border:1px solid #9ca3af;padding:10px;text-align:left;">Mô tả</th>
            <th style="border:1px solid #9ca3af;padding:10px;text-align:left;">Ngày gửi</th>
            <th style="border:1px solid #9ca3af;padding:10px;text-align:left;">Người gửi</th>
            <th style="border:1px solid #9ca3af;padding:10px;text-align:left;">Mã nhân viên</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td style="border:1px solid #9ca3af;padding:10px;vertical-align:top;">{escape((idea.title or "").strip() or f"Ý tưởng #{idea.id}")}</td>
            <td style="border:1px solid #9ca3af;padding:10px;vertical-align:top;white-space:pre-wrap;">{escape((idea.description or "").strip())}</td>
            <td style="border:1px solid #9ca3af;padding:10px;vertical-align:top;">{escape(_format_submitted_at(idea.submitted_at))}</td>
            <td style="border:1px solid #9ca3af;padding:10px;vertical-align:top;">{escape((idea.full_name or "").strip())}</td>
            <td style="border:1px solid #9ca3af;padding:10px;vertical-align:top;">{escape((idea.employee_code or "").strip())}</td>
          </tr>
        </tbody>
      </table>
    """


def _table_text(idea: Idea) -> str:
    return (
        f"Tên ý tưởng: {(idea.title or '').strip() or f'Ý tưởng #{idea.id}'}\n"
        f"Mô tả: {(idea.description or '').strip()}\n"
        f"Ngày gửi: {_format_submitted_at(idea.submitted_at)}\n"
        f"Người gửi: {(idea.full_name or '').strip()}\n"
        f"Mã nhân viên: {(idea.employee_code or '').strip()}\n"
    )


def _build_html(context: ApprovalEmailContext) -> str:
    action_html = ""
    if context.action_url:
        action_text = context.action_text or "thực hiện"
        action_html = f"""
        <p>
          Vui lòng truy cập link:
          <a href="{escape(context.action_url)}" style="color:#0f2f7f;font-weight:700;">
            {escape(context.action_url)}
          </a>
          để {escape(action_text)}.
        </p>
        """
    idea_table_html = _table_html(context.idea) if context.show_idea_table else ""
    return f"""
      <div style="font-family:Arial,Helvetica,sans-serif;font-size:16px;line-height:1.6;color:#111827;">
        <p><strong>Kính gửi {escape(context.greeting_name)},</strong></p>
        <p>{escape(context.content_line)}</p>
        {action_html}
        {idea_table_html}
        {context.extra_html}
        {EMAIL_FOOTER_HTML}
      </div>
    """


def _build_text(context: ApprovalEmailContext) -> str:
    action_text = ""
    if context.action_url:
        action_label = context.action_text or "thực hiện"
        action_text = f"Vui lòng truy cập link: {context.action_url} để {action_label}.\n\n"
    extra_text = f"\n{context.extra_text.strip()}\n" if context.extra_text.strip() else ""
    idea_table_text = f"{_table_text(context.idea)}" if context.show_idea_table else ""
    return (
        f"Kính gửi {context.greeting_name},\n\n"
        f"{context.content_line}\n\n"
        f"{action_text}"
        f"{idea_table_text}"
        f"{extra_text}\n"
        f"{EMAIL_FOOTER_TEXT}"
    )


def _send_email(recipients: list[str], subject: str, html_body: str, text_body: str) -> None:
    if not recipients:
        return
    if not _email_enabled():
        print(f"WARN: SMTP not configured, skip email '{subject}' to {recipients}")
        return

    host, username, password, from_email = _smtp_runtime_config()

    message = EmailMessage()
    from_name = (settings.SMTP_FROM_NAME or "").strip()
    message["Subject"] = subject
    message["From"] = f"{from_name} <{from_email}>" if from_name else from_email
    message["To"] = ", ".join(recipients)
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    if settings.SMTP_USE_SSL:
        with smtplib.SMTP_SSL(host, settings.SMTP_PORT, context=ssl.create_default_context()) as smtp:
            if username:
                smtp.login(username, password)
            smtp.send_message(message)
        return

    with smtplib.SMTP(host, settings.SMTP_PORT) as smtp:
        smtp.ehlo()
        if settings.SMTP_USE_TLS:
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()
        if username:
            smtp.login(username, password)
        smtp.send_message(message)


def _parse_json_list(raw_value: str | None) -> list[str]:
    if not raw_value:
        return []
    try:
        parsed = json.loads(raw_value)
    except (TypeError, json.JSONDecodeError):
        return []
    return [str(item) for item in parsed] if isinstance(parsed, list) else []


def _normalize_status(value: object) -> str:
    if value is None:
        return ""
    return str(value).split(".")[-1]


def _criteria_label_lookup(db: Session) -> dict[tuple[str, str], str]:
    rows = (
        db.query(ScoreCriteria)
        .filter(ScoreCriteria.is_active.is_(True))
        .order_by(ScoreCriteria.criterion_key.asc(), ScoreCriteria.sort_order.asc(), ScoreCriteria.id.asc())
        .all()
    )
    lookup: dict[tuple[str, str], str] = {}
    for row in rows:
        lookup[(row.criterion_key, row.code)] = row.label
    return lookup


def _latest_ie_score(idea: Idea) -> IdeaScore | None:
    ie_scores = [score for score in idea.scores if score.scorer and score.scorer.role == UserRole.IE_MANAGER.value]
    if not ie_scores:
        return None
    ie_scores.sort(key=lambda item: (item.scored_at or datetime.min, item.id or 0), reverse=True)
    return ie_scores[0]


def _latest_council_result_type(idea: Idea) -> str | None:
    ordered = sorted(idea.reviews, key=lambda item: (item.reviewed_at or datetime.min, item.id or 0), reverse=True)
    for review in ordered:
        if _normalize_status(review.level) == ReviewLevel.COUNCIL.value and review.council_result_type:
            return review.council_result_type.strip().upper()
    return None


def _display_lines_html(lines: list[str]) -> str:
    return "<br>".join(escape(line) for line in lines if line)


def _display_lines_text(lines: list[str]) -> str:
    return "; ".join(line for line in lines if line) or "Không có"


def _score_detail_rows(score: IdeaScore, labels: dict[tuple[str, str], str]) -> list[dict[str, str | int]]:
    k1_code = _normalize_status(score.k1_type)
    k1_label = labels.get(("K1", k1_code), K1_FALLBACK_LABELS.get(k1_code, k1_code or ""))

    k2_type = _normalize_status(score.k2_type)
    k2_group = "K2_HARD" if k2_type in {K2Type.HARD.value, K2Type.NORMAL_HARD.value} else "K2_EASY"
    k2_codes = _parse_json_list(score.k2_selected_codes)
    k2_lines = [K2_TYPE_LABELS.get(k2_type, k2_type or "K2")] + [
        labels.get((k2_group, code), code) for code in k2_codes
    ]

    k3_type = _normalize_status(score.k3_measure_type)
    if k3_type == K3MeasureType.UNMEASURABLE.value:
        k3_lines = [K3_MEASURE_LABELS.get(k3_type, k3_type or "K3")] + [
            labels.get(("K3_UNMEASURABLE", code), code) for code in _parse_json_list(score.k3_selected_codes)
        ]
    else:
        group_key = "K3_TIME_SAVED" if k3_type == K3MeasureType.TIME_SAVED.value else "K3_COST_SAVED"
        option_label = labels.get((group_key, score.k3_option_code or ""), score.k3_option_code or "")
        k3_lines = [K3_MEASURE_LABELS.get(k3_type, k3_type or "K3"), option_label]

    rows: list[dict[str, str | int]] = [
        {
            "criterion": "K1",
            "content_html": _display_lines_html([k1_label]),
            "content_text": k1_label or "Không có",
            "score": score.k1_score,
            "note": score.k1_note or "",
        },
        {
            "criterion": "K2",
            "content_html": _display_lines_html(k2_lines),
            "content_text": _display_lines_text(k2_lines),
            "score": score.k2_score,
            "note": score.k2_note or "",
        },
        {
            "criterion": "K3",
            "content_html": _display_lines_html(k3_lines),
            "content_text": _display_lines_text(k3_lines),
            "score": score.k3_score,
            "note": score.k3_note or "",
        },
    ]
    return rows


def _ie_score_summary_html(db: Session, idea: Idea, result_label: str) -> str:
    score = _latest_ie_score(idea)
    if score is None:
        return ""
    labels = _criteria_label_lookup(db)
    rows = _score_detail_rows(score, labels)
    body_rows = "".join(
        f"""
          <tr>
            <td style="border:1px solid #9ca3af;padding:10px;vertical-align:top;font-weight:700;">{escape(str(row["criterion"]))}</td>
            <td style="border:1px solid #9ca3af;padding:10px;vertical-align:top;">{row["content_html"]}</td>
            <td style="border:1px solid #9ca3af;padding:10px;vertical-align:top;text-align:center;font-weight:700;">{row["score"]}</td>
            <td style="border:1px solid #9ca3af;padding:10px;vertical-align:top;white-space:pre-wrap;">{escape(str(row["note"])) or "—"}</td>
          </tr>
        """
        for row in rows
    )
    return f"""
      <div style="margin:20px 0 0;">
        <p style="margin:0 0 10px;"><strong>Kết luận Ban cải tiến:</strong> {escape(result_label)}</p>
        <table style="border-collapse:collapse;width:100%;margin:0 0 20px;">
          <thead>
            <tr style="background:#0f2f7f;color:#ffffff;">
              <th style="border:1px solid #9ca3af;padding:10px;text-align:left;">Tiêu chí</th>
              <th style="border:1px solid #9ca3af;padding:10px;text-align:left;">Nội dung chấm</th>
              <th style="border:1px solid #9ca3af;padding:10px;text-align:center;">Điểm</th>
              <th style="border:1px solid #9ca3af;padding:10px;text-align:left;">Ghi chú</th>
            </tr>
          </thead>
          <tbody>
            {body_rows}
            <tr style="background:#eff6ff;">
              <td colspan="2" style="border:1px solid #9ca3af;padding:10px;text-align:right;font-weight:700;">Tổng điểm</td>
              <td style="border:1px solid #9ca3af;padding:10px;text-align:center;font-weight:700;">{score.total_score}</td>
              <td style="border:1px solid #9ca3af;padding:10px;">&nbsp;</td>
            </tr>
          </tbody>
        </table>
      </div>
    """


def _ie_score_summary_text(db: Session, idea: Idea, result_label: str) -> str:
    score = _latest_ie_score(idea)
    if score is None:
        return f"Kết luận Ban cải tiến: {result_label}"
    labels = _criteria_label_lookup(db)
    rows = _score_detail_rows(score, labels)
    lines = [f"Kết luận Ban cải tiến: {result_label}", "Bảng điểm Ban cải tiến:"]
    for row in rows:
        note = f" | Ghi chú: {row['note']}" if row["note"] else ""
        lines.append(
            f"- {row['criterion']}: {row['content_text']} | Điểm: {row['score']}{note}"
        )
    lines.append(f"- Tổng điểm: {score.total_score}")
    return "\n".join(lines)


def _build_ie_result_context(db: Session, idea: Idea) -> ApprovalEmailContext | None:
    result_type = _latest_council_result_type(idea)
    result_label = IE_RESULT_LABELS.get(result_type or "")
    message = IE_RESULT_MESSAGES.get(result_type or "")
    if not result_label or not message:
        return None

    recipients = _query_unit_leadership_recipients(db, idea)
    if not recipients:
        return None

    unit_name = (idea.unit.name if idea.unit else "") or "đơn vị"
    extra_html = ""
    extra_text = f"Kết luận Ban cải tiến: {result_label}"
    if result_type in {IE_RESULT_APPROVED_NO_STANDARDIZATION, IE_RESULT_APPROVED_STANDARDIZATION}:
        extra_html = _ie_score_summary_html(db, idea, result_label)
        extra_text = _ie_score_summary_text(db, idea, result_label)

    return ApprovalEmailContext(
        recipients=recipients,
        greeting_name=unit_name,
        subject=f"[Ý tưởng vàng] Kết quả xét duyệt cấp 2 - {idea.title}",
        content_line=message,
        action_url=settings.APPROVAL_PAGE_URL,
        action_text="theo dõi trạng thái xét duyệt",
        idea=idea,
        extra_html=extra_html,
        extra_text=extra_text,
    )


def _format_money(value: int | float) -> str:
    return f"{int(round(float(value))):,}".replace(",", ".")


def _reward_multiplier_for_idea(idea: Idea) -> float:
    value = getattr(idea, "council_reward_multiplier", None)
    if value is None:
        return 1.0
    return float(value)


def _reward_batch_summary_html(quarter: int, year: int, items: list[dict[str, object]]) -> str:
    rows = "".join(
        f"""
          <tr>
            <td style="border:1px solid #9ca3af;padding:10px;text-align:center;vertical-align:top;">{index}</td>
            <td style="border:1px solid #9ca3af;padding:10px;vertical-align:top;">{escape(str(item["title"]))}</td>
            <td style="border:1px solid #9ca3af;padding:10px;vertical-align:top;white-space:pre-wrap;">{escape(str(item["description"])) or "—"}</td>
            <td style="border:1px solid #9ca3af;padding:10px;text-align:center;vertical-align:top;font-weight:700;">{item["score"]}</td>
            <td style="border:1px solid #9ca3af;padding:10px;text-align:right;vertical-align:top;font-weight:700;">{escape(_format_money(item["amount"]))} VND</td>
          </tr>
        """
        for index, item in enumerate(items, start=1)
    )
    return f"""
      <div style="margin:20px 0 0;">
        <table style="border-collapse:collapse;width:100%;margin:0 0 20px;">
          <thead>
            <tr style="background:#0f2f7f;color:#ffffff;">
              <th style="border:1px solid #9ca3af;padding:10px;text-align:center;">STT</th>
              <th style="border:1px solid #9ca3af;padding:10px;text-align:left;">Tên ý tưởng</th>
              <th style="border:1px solid #9ca3af;padding:10px;text-align:left;">Mô tả</th>
              <th style="border:1px solid #9ca3af;padding:10px;text-align:center;">Điểm xét duyệt</th>
              <th style="border:1px solid #9ca3af;padding:10px;text-align:right;">Tiền thưởng</th>
            </tr>
          </thead>
          <tbody>
            {rows}
          </tbody>
        </table>
      </div>
    """


def _reward_batch_summary_text(quarter: int, year: int, items: list[dict[str, object]]) -> str:
    lines: list[str] = []
    for index, item in enumerate(items, start=1):
        lines.append(
            f"{index}. {item['title']} | Điểm xét duyệt: {item['score']} | Tiền thưởng: {_format_money(item['amount'])} VND"
        )
        description = str(item["description"] or "").strip()
        if description:
            lines.append(f"   Mô tả: {description}")
    return "\n".join(lines)


def send_reward_batch_summary_emails(
    db: Session,
    batch: RewardBatch,
    ideas: list[Idea],
    special_rewards: dict[int, float] | None = None,
) -> None:
    special_rewards = special_rewards or {}
    grouped: dict[int, dict[str, object]] = {}

    for idea in ideas:
        if idea.unit_id is None or idea.council_final_score is None:
            continue
        reward_multiplier = float(special_rewards.get(int(idea.id), _reward_multiplier_for_idea(idea)))
        amount = round(int(idea.council_final_score) * float(batch.coefficient) * reward_multiplier)
        unit_name = (idea.unit.name if idea.unit else "") or "đơn vị"
        payload = grouped.setdefault(
            int(idea.unit_id),
            {
                "unit_name": unit_name,
                "recipients": _query_unit_leadership_recipients(db, idea),
                "items": [],
            },
        )
        payload["items"].append(
            {
                "title": (idea.title or "").strip() or f"Ý tưởng #{idea.id}",
                "description": (idea.description or "").strip(),
                "score": int(idea.council_final_score),
                "amount": amount,
            }
        )

    for payload in grouped.values():
        recipients = payload["recipients"]
        items = payload["items"]
        unit_name = payload["unit_name"]
        if not recipients or not items:
            continue

        subject = f"Kết quả Khen thưởng YTV Q{int(batch.quarter)}/{int(batch.year)} - {unit_name}"
        context = ApprovalEmailContext(
            recipients=list(recipients),
            greeting_name=str(unit_name),
            subject=subject,
            content_line=(
                f"Chúc mừng các ý tưởng của đơn vị bạn đã được Hội đồng xác nhận kết quả trong "
                f"Q{int(batch.quarter)}/{int(batch.year)}."
            ),
            idea=ideas[0],
            extra_html=_reward_batch_summary_html(int(batch.quarter), int(batch.year), list(items)),
            extra_text=_reward_batch_summary_text(int(batch.quarter), int(batch.year), list(items)),
            show_idea_table=False,
        )
        try:
            _send_email(
                context.recipients,
                context.subject,
                _build_html(context),
                _build_text(context),
            )
        except Exception as exc:
            print(
                f"WARN: failed to send reward batch summary email for quarter={batch.quarter}, "
                f"year={batch.year}, unit={unit_name}: {exc}"
            )


def _build_stage_context(db: Session, idea: Idea, stage: str) -> ApprovalEmailContext | None:
    unit_name = (idea.unit.name if idea.unit else "") or "đơn vị"

    if stage == "dept_review":
        recipients = _query_dept_manager_recipients(db, idea)
        return ApprovalEmailContext(
            recipients=recipients,
            greeting_name=unit_name,
            subject=f"[Ý tưởng vàng] Ý tưởng mới chờ duyệt cấp 1 - {idea.title}",
            content_line=f"Có ý tưởng mới cần được xét duyệt bởi {unit_name} cấp 1.",
            action_url=settings.APPROVAL_PAGE_URL,
            action_text="xử lý",
            idea=idea,
        )
    if stage == "ie_review":
        recipients = _query_role_recipients(db, UserRole.IE_MANAGER.value)
        return ApprovalEmailContext(
            recipients=recipients,
            greeting_name="Ban cải tiến",
            subject=f"[Ý tưởng vàng] Ý tưởng chờ duyệt cấp 2 - {idea.title}",
            content_line="Có ý tưởng mới cần được xét duyệt bởi Ban cải tiến - cấp 2.",
            action_url=settings.APPROVAL_PAGE_URL,
            action_text="xử lý",
            idea=idea,
        )
    if stage == "ie_result_notice":
        return _build_ie_result_context(db, idea)
    if stage == "bod_review":
        recipients = _query_role_recipients(db, UserRole.BOD_MANAGER.value)
        return ApprovalEmailContext(
            recipients=recipients,
            greeting_name="Lãnh đạo Công ty",
            subject=f"[Ý tưởng vàng] Ý tưởng chờ duyệt cấp 3 - {idea.title}",
            content_line="Có ý tưởng mới cần được xét duyệt bởi Lãnh đạo Công ty - cấp 3.",
            action_url=settings.APPROVAL_PAGE_URL,
            action_text="xử lý",
            idea=idea,
        )
    if stage == "approved_notice":
        recipients = _query_dept_manager_recipients(db, idea)
        return ApprovalEmailContext(
            recipients=recipients,
            greeting_name=unit_name,
            subject=f"[Ý tưởng vàng] Ý tưởng đã được xét duyệt thành công - {idea.title}",
            content_line=f"Ý tưởng của {unit_name} đã được xét duyệt thành công qua đủ 3 cấp.",
            action_url=settings.APPROVAL_PAGE_URL,
            action_text="theo dõi",
            idea=idea,
        )
    return None


def send_approval_stage_email(db: Session, idea: Idea, stage: str) -> None:
    context = _build_stage_context(db, idea, stage)
    if context is None or not context.recipients:
        return
    try:
        _send_email(
            context.recipients,
            context.subject,
            _build_html(context),
            _build_text(context),
        )
    except Exception as exc:
        print(f"WARN: failed to send approval email for idea_id={idea.id}, stage={stage}: {exc}")
