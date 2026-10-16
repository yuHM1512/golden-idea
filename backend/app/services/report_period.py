from datetime import UTC, datetime

from sqlalchemy import and_, or_

from app.time_utils import DISPLAY_TIME_ZONE, to_display_tz


def default_report_period(idea):
    """Use the idea date shown in the detailed register, in local business time."""
    local_date = to_display_tz(idea.submitted_at)
    if local_date is None:
        return None
    return local_date.year, (local_date.month - 1) // 3 + 1


def effective_report_period(idea):
    if idea.report_year is not None and idea.report_quarter is not None:
        return int(idea.report_year), int(idea.report_quarter)
    return default_report_period(idea)


def report_period_predicate(idea_model, year: int, quarter: int, dialect_name: str):
    """SQL predicate matching effective_report_period, including local business dates."""
    first_month = (int(quarter) - 1) * 3 + 1
    next_year = int(year) + (1 if first_month == 10 else 0)
    next_month = 1 if first_month == 10 else first_month + 3
    local_start = datetime(int(year), first_month, 1, tzinfo=DISPLAY_TIME_ZONE)
    local_end = datetime(next_year, next_month, 1, tzinfo=DISPLAY_TIME_ZONE)
    start_utc = local_start.astimezone(UTC)
    end_utc = local_end.astimezone(UTC)
    if dialect_name == "sqlite":
        start_utc = start_utc.replace(tzinfo=None)
        end_utc = end_utc.replace(tzinfo=None)

    explicit_period = and_(idea_model.report_year == int(year), idea_model.report_quarter == int(quarter))
    default_period = and_(
        or_(idea_model.report_year.is_(None), idea_model.report_quarter.is_(None)),
        idea_model.submitted_at >= start_utc,
        idea_model.submitted_at < end_utc,
    )
    return or_(explicit_period, default_period)
