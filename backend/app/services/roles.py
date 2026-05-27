import json
import unicodedata
from enum import Enum
from typing import Iterable

from app.models.user import User, UserRole


ROLE_PRIORITY = [
    UserRole.ADMIN.value,
    UserRole.DEPT_MANAGER.value,
    UserRole.SUB_DEPT_MANAGER.value,
    UserRole.DIGITAL_MANAGER.value,
    UserRole.IE_MANAGER.value,
    UserRole.BOD_MANAGER.value,
    UserRole.UNIT_REPRESENT.value,
    UserRole.TREASURER.value,
    UserRole.EMPLOYEE.value,
]


def normalize_roles(values: Iterable[str | UserRole | None] | None, fallback: str | None = None) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    source = list(values or [])
    if fallback:
        parsed_fallback = parse_roles_value(fallback)
        source.extend(parsed_fallback or [fallback])
    for value in source:
        raw = value.value if isinstance(value, Enum) else str(value or "")
        role = raw.strip().lower()
        if not role or role in seen:
            continue
        try:
            role = UserRole(role).value
        except ValueError:
            continue
        seen.add(role)
        result.append(role)
    return result or [UserRole.EMPLOYEE.value]


def user_roles(user: User | None) -> list[str]:
    if user is None:
        return []
    return parse_roles_value(user.role)


def set_user_roles(user: User, roles: Iterable[str | UserRole | None]) -> None:
    normalized = normalize_roles(roles)
    user.role = json.dumps(normalized, ensure_ascii=False)


def parse_roles_value(value: object) -> list[str]:
    if isinstance(value, list):
        return normalize_roles(value)
    raw = str(value or "").strip()
    if not raw:
        return [UserRole.EMPLOYEE.value]
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        parsed = None
    if isinstance(parsed, list):
        return normalize_roles(parsed)
    return normalize_roles([raw])


def primary_role(roles: Iterable[str]) -> str:
    role_set = set(normalize_roles(roles))
    for role in ROLE_PRIORITY:
        if role in role_set:
            return role
    return UserRole.EMPLOYEE.value


def has_role(user: User | None, role: str | UserRole) -> bool:
    raw = role.value if isinstance(role, UserRole) else str(role)
    return raw in user_roles(user)


def _fold_text(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value or "")
    without_marks = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return without_marks.casefold().strip()


def is_digitization_category(value: object) -> bool:
    text = str(value or "").strip()
    folded = _fold_text(text)
    return (
        text.upper() == "DIGITIZATION"
        or folded in {"so hoa", "sohoa", "digitization"}
        or (folded.startswith("s") and "ho" in folded)
    )
