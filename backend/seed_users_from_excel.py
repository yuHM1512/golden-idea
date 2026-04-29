from __future__ import annotations

import argparse
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from sqlalchemy.exc import IntegrityError

from app.database import Base, SessionLocal, engine
from app.models.unit import Unit
from app.models.user import User, UserRole
from app.seed import (
    migrate_user_role_column,
    migrate_users_unit_nullable,
    normalize_employee_codes,
    seed_admin_user,
    seed_units,
)


REQUIRED_HEADERS = ("employee_code", "full_name", "unit_id", "role")
ROLE_WITHOUT_UNIT = {
    UserRole.ADMIN.value,
    UserRole.TREASURER.value,
    UserRole.BOD_MANAGER.value,
}
NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


@dataclass
class UserSeedRow:
    employee_code: str
    full_name: str
    unit_id: int | None
    role: str


def column_index_from_ref(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha()).upper()
    value = 0
    for ch in letters:
        value = value * 26 + (ord(ch) - ord("A") + 1)
    return value - 1


def normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def parse_unit_id(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        raise ValueError(f"unit_id không hợp lệ: {value}")

    text = str(value).strip()
    if not text:
        return None
    if text.endswith(".0"):
        text = text[:-2]
    return int(text)


def _load_shared_strings(workbook: zipfile.ZipFile) -> list[str]:
    try:
        raw = workbook.read("xl/sharedStrings.xml")
    except KeyError:
        return []

    root = ET.fromstring(raw)
    shared_strings: list[str] = []
    for item in root.findall("main:si", NS):
        parts = [node.text or "" for node in item.findall(".//main:t", NS)]
        shared_strings.append("".join(parts))
    return shared_strings


def _get_first_sheet_path(workbook: zipfile.ZipFile) -> str:
    workbook_root = ET.fromstring(workbook.read("xl/workbook.xml"))
    first_sheet = workbook_root.find("main:sheets/main:sheet", NS)
    if first_sheet is None:
        raise ValueError("Workbook không có sheet nào")

    rel_id = first_sheet.attrib.get(f"{{{NS['rel']}}}id")
    if not rel_id:
        raise ValueError("Không đọc được quan hệ của sheet đầu tiên")

    rels_root = ET.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
    for rel in rels_root.findall("pkgrel:Relationship", NS):
        if rel.attrib.get("Id") == rel_id:
            target = rel.attrib["Target"].lstrip("/")
            if target.startswith("worksheets/"):
                return f"xl/{target}"
            if target.startswith("xl/"):
                return target
            return f"xl/{target}"
    raise ValueError("Không tìm thấy file sheet đầu tiên trong workbook")


def _parse_sheet_rows(sheet_xml: bytes, shared_strings: list[str]) -> list[list[Any]]:
    root = ET.fromstring(sheet_xml)
    rows: list[list[Any]] = []

    for row in root.findall(".//main:sheetData/main:row", NS):
        values_by_index: dict[int, Any] = {}
        max_index = -1

        for cell in row.findall("main:c", NS):
            cell_ref = cell.attrib.get("r", "")
            col_index = column_index_from_ref(cell_ref)
            max_index = max(max_index, col_index)

            cell_type = cell.attrib.get("t")
            value_node = cell.find("main:v", NS)

            if cell_type == "inlineStr":
                text_parts = [node.text or "" for node in cell.findall(".//main:t", NS)]
                cell_value: Any = "".join(text_parts)
            elif value_node is None:
                cell_value = None
            else:
                raw_value = value_node.text
                if cell_type == "s":
                    cell_value = shared_strings[int(raw_value)] if raw_value is not None else None
                else:
                    cell_value = raw_value

            values_by_index[col_index] = cell_value

        if max_index < 0:
            rows.append([])
            continue

        rows.append([values_by_index.get(idx) for idx in range(max_index + 1)])

    return rows


def load_users_from_xlsx(file_path: Path) -> list[UserSeedRow]:
    with zipfile.ZipFile(file_path) as workbook:
        shared_strings = _load_shared_strings(workbook)
        sheet_path = _get_first_sheet_path(workbook)
        rows = _parse_sheet_rows(workbook.read(sheet_path), shared_strings)

    if not rows:
        raise ValueError("File Excel không có dữ liệu")

    headers = tuple((normalize_text(value) or "") for value in rows[0])
    if headers[: len(REQUIRED_HEADERS)] != REQUIRED_HEADERS:
        raise ValueError(
            f"Header không đúng. Cần {REQUIRED_HEADERS}, nhận được {headers}"
        )

    result: list[UserSeedRow] = []
    for index, raw_row in enumerate(rows[1:], start=2):
        padded = list(raw_row) + [None] * max(0, len(REQUIRED_HEADERS) - len(raw_row))
        employee_code = normalize_text(padded[0])
        full_name = normalize_text(padded[1])
        role = normalize_text(padded[3])
        unit_id = parse_unit_id(padded[2])

        if not any(normalize_text(value) for value in padded[: len(REQUIRED_HEADERS)]):
            continue
        if not employee_code:
            raise ValueError(f"Dòng {index}: thiếu employee_code")
        if not full_name:
            raise ValueError(f"Dòng {index}: thiếu full_name")
        if not role:
            raise ValueError(f"Dòng {index}: thiếu role")

        result.append(
            UserSeedRow(
                employee_code=employee_code.upper(),
                full_name=full_name,
                unit_id=unit_id,
                role=role.strip().lower(),
            )
        )

    return result


def initialize_database() -> None:
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    migrate_user_role_column()
    migrate_users_unit_nullable()
    normalize_employee_codes()
    seed_units()
    seed_admin_user()


def validate_rows(rows: list[UserSeedRow], units_by_id: dict[int, Unit]) -> None:
    seen_codes: set[str] = set()
    valid_roles = {role.value for role in UserRole}

    for idx, row in enumerate(rows, start=2):
        if row.employee_code in seen_codes:
            raise ValueError(f"Dòng {idx}: employee_code bị trùng trong file ({row.employee_code})")
        seen_codes.add(row.employee_code)

        if row.role not in valid_roles:
            raise ValueError(f"Dòng {idx}: role không hợp lệ ({row.role})")

        if row.role not in ROLE_WITHOUT_UNIT and row.unit_id is None:
            raise ValueError(f"Dòng {idx}: role {row.role} bắt buộc có unit_id")

        if row.unit_id is not None and row.unit_id not in units_by_id:
            raise ValueError(f"Dòng {idx}: unit_id {row.unit_id} không tồn tại trong database")


def assign_dept_manager_if_needed(units_by_id: dict[int, Unit], user: User) -> None:
    if user.role != UserRole.DEPT_MANAGER.value or user.unit_id is None:
        return
    unit = units_by_id.get(user.unit_id)
    if unit is not None:
        unit.manager_user_id = user.id


def upsert_users(rows: list[UserSeedRow], dry_run: bool) -> tuple[int, int]:
    db = SessionLocal()
    try:
        units_by_id = {unit.id: unit for unit in db.query(Unit).all()}
        validate_rows(rows, units_by_id)

        employee_codes = [row.employee_code for row in rows]
        existing_users = (
            db.query(User)
            .filter(User.employee_code.in_(employee_codes))
            .all()
        )
        users_by_code = {user.employee_code.upper(): user for user in existing_users}

        inserted = 0
        updated = 0

        for row in rows:
            user = users_by_code.get(row.employee_code)
            if user is None:
                user = User(employee_code=row.employee_code)
                db.add(user)
                users_by_code[row.employee_code] = user
                inserted += 1
            else:
                updated += 1

            user.employee_code = row.employee_code
            user.full_name = row.full_name
            user.unit_id = row.unit_id
            user.role = row.role
            user.is_active = True

        db.flush()

        managed_users = (
            db.query(User)
            .filter(
                User.employee_code.in_(employee_codes),
                User.role == UserRole.DEPT_MANAGER.value,
            )
            .all()
        )
        for user in managed_users:
            assign_dept_manager_if_needed(units_by_id, user)

        if dry_run:
            db.rollback()
        else:
            db.commit()

        return inserted, updated
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("Seed thất bại do trùng employee_code hoặc email trong database") from exc
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def build_parser() -> argparse.ArgumentParser:
    default_file = Path(__file__).with_name("users_seed.xlsx")

    parser = argparse.ArgumentParser(
        description="Seed users từ file Excel vào database Golden Idea"
    )
    parser.add_argument(
        "--file",
        default=str(default_file),
        help="Đường dẫn file users_seed.xlsx",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Kiểm tra và giả lập seed, rollback sau khi hoàn tất",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Chỉ đọc file, kiểm tra dữ liệu và mapping unit/role, không ghi database",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    file_path = Path(args.file).resolve()
    if not file_path.exists():
        print(f"Không tìm thấy file Excel: {file_path}", file=sys.stderr)
        return 1

    try:
        rows = load_users_from_xlsx(file_path)
        initialize_database()

        db = SessionLocal()
        try:
            units_by_id = {unit.id: unit for unit in db.query(Unit).order_by(Unit.id.asc()).all()}
        finally:
            db.close()

        validate_rows(rows, units_by_id)

        if args.validate_only:
            print(f"Đã kiểm tra hợp lệ {len(rows)} user từ {file_path}")
            print(f"Unit ids có trong file: {sorted({row.unit_id for row in rows if row.unit_id is not None})}")
            print(f"Roles có trong file: {sorted({row.role for row in rows})}")
            return 0

        inserted, updated = upsert_users(rows, dry_run=args.dry_run)
        action = "DRY RUN thành công" if args.dry_run else "Seed thành công"
        print(f"{action}: {len(rows)} dòng hợp lệ, inserted={inserted}, updated={updated}")
        return 0
    except Exception as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
