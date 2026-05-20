from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

try:
    DISPLAY_TIME_ZONE = ZoneInfo("Asia/Bangkok")
except ZoneInfoNotFoundError:
    DISPLAY_TIME_ZONE = timezone(timedelta(hours=7))


def now_utc() -> datetime:
    return datetime.now(UTC)


def to_display_tz(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(DISPLAY_TIME_ZONE)


def now_display_tz() -> datetime:
    return to_display_tz(now_utc()) or now_utc()


def format_display_datetime(value: datetime | None, fmt: str = "%d/%m/%Y %H:%M") -> str:
    converted = to_display_tz(value)
    return converted.strftime(fmt) if converted else ""
