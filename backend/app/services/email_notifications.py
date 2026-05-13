from __future__ import annotations

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
from app.models.unit import Unit
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


@dataclass
class ApprovalEmailContext:
    recipients: list[str]
    greeting_name: str
    subject: str
    content_line: str
    idea: Idea


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
    return f"""
      <div style="font-family:Arial,Helvetica,sans-serif;font-size:16px;line-height:1.6;color:#111827;">
        <p><strong>Kính gửi {escape(context.greeting_name)},</strong></p>
        <p>{escape(context.content_line)}</p>
        <p>
          Vui lòng truy cập link:
          <a href="{escape(settings.APPROVAL_PAGE_URL)}" style="color:#0f2f7f;font-weight:700;">
            {escape(settings.APPROVAL_PAGE_URL)}
          </a>
          để xử lý.
        </p>
        {_table_html(context.idea)}
        {EMAIL_FOOTER_HTML}
      </div>
    """


def _build_text(context: ApprovalEmailContext) -> str:
    return (
        f"Kính gửi {context.greeting_name},\n\n"
        f"{context.content_line}\n\n"
        f"Vui lòng truy cập link: {settings.APPROVAL_PAGE_URL} để xử lý.\n\n"
        f"{_table_text(context.idea)}\n"
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


def _build_stage_context(db: Session, idea: Idea, stage: str) -> ApprovalEmailContext | None:
    unit_name = (idea.unit.name if idea.unit else "") or "đơn vị"

    if stage == "dept_review":
        recipients = _query_dept_manager_recipients(db, idea)
        return ApprovalEmailContext(
            recipients=recipients,
            greeting_name=unit_name,
            subject=f"[Ý tưởng vàng] Ý tưởng mới chờ duyệt cấp 1 - {idea.title}",
            content_line=f"Có ý tưởng mới cần được xét duyệt bởi {unit_name} cấp 1.",
            idea=idea,
        )
    if stage == "ie_review":
        recipients = _query_role_recipients(db, UserRole.IE_MANAGER.value)
        return ApprovalEmailContext(
            recipients=recipients,
            greeting_name="Ban cải tiến",
            subject=f"[Ý tưởng vàng] Ý tưởng chờ duyệt cấp 2 - {idea.title}",
            content_line="Có ý tưởng mới cần được xét duyệt bởi Ban cải tiến - cấp 2.",
            idea=idea,
        )
    if stage == "bod_review":
        recipients = _query_role_recipients(db, UserRole.BOD_MANAGER.value)
        return ApprovalEmailContext(
            recipients=recipients,
            greeting_name="Lãnh đạo Công ty",
            subject=f"[Ý tưởng vàng] Ý tưởng chờ duyệt cấp 3 - {idea.title}",
            content_line="Có ý tưởng mới cần được xét duyệt bởi Lãnh đạo Công ty - cấp 3.",
            idea=idea,
        )
    if stage == "approved_notice":
        recipients = _query_dept_manager_recipients(db, idea)
        return ApprovalEmailContext(
            recipients=recipients,
            greeting_name=unit_name,
            subject=f"[Ý tưởng vàng] Ý tưởng đã được xét duyệt thành công - {idea.title}",
            content_line=f"Ý tưởng của {unit_name} đã được xét duyệt thành công qua đủ 3 cấp.",
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
