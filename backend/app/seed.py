from __future__ import annotations

from datetime import date

from sqlalchemy import inspect, text

from app.database import SessionLocal
from app.models.score_criteria import ScoreCriteria
from app.models.score_criteria_set import ScoreCriteriaSet
from app.models.unit import Unit
from app.models.user import User, UserRole
from app.database import engine


UNITS_SEED: list[dict[str, str]] = [
    {"name": "P. Tổng hợp", "department": "Phòng ban"},
    {"name": "P. KDXNK", "department": "Phòng ban"},
    {"name": "P. KTCN", "department": "Phòng ban"},
    {"name": "P. QLCL", "department": "Phòng ban"},
    {"name": "P. KTCĐ & ĐTMT", "department": "Phòng ban"},
    {"name": "Ban Thiết bị", "department": "Phòng ban"},
    {"name": "XNDT", "department": "Xí nghiệp"},
    {"name": "XN2", "department": "Xí nghiệp"},
    {"name": "XN3", "department": "Xí nghiệp"},
    {"name": "XNV2", "department": "Xí nghiệp"},
    {"name": "XN1-V1", "department": "Xí nghiệp"},
    {"name": "P. QTĐS", "department": "Phòng ban"},
    {"name": "P. KT", "department": "Phòng ban"},
    {"name": "Y tế", "department": "Phòng ban"},
    {"name": "Phòng Lab", "department": "Phòng ban"},
]

SCORE_CRITERIA_SEED: list[dict[str, object]] = [
    {
        "criterion_key": "K1",
        "code": "A1",
        "label": "Ý tưởng hoàn toàn mới",
        "tooltip": "Chưa được đăng ký hoặc triển khai trong công ty.",
        "note": "Có thể ứng dụng từ ngành khác cho ngành may.",
        "score": 10,
        "input_type": "radio",
        "sort_order": 1,
    },
    {
        "criterion_key": "K1",
        "code": "A2",
        "label": "Có cải tiến bổ sung từ ý tưởng cũ",
        "tooltip": "Trên cơ sở ý tưởng đã có tại công ty.",
        "note": "Có thay đổi khá nhiều hoặc kết cấu phức tạp.",
        "score": 5,
        "input_type": "radio",
        "sort_order": 2,
    },
    {
        "criterion_key": "K1",
        "code": "A3",
        "label": "Ý tưởng cũ",
        "tooltip": "Đã có ở M29.",
        "note": "Chỉ thay đổi thông số hoặc thay đổi kết cấu nhỏ.",
        "score": 2,
        "input_type": "radio",
        "sort_order": 3,
    },
    {
        "criterion_key": "K2_EASY",
        "code": "B1",
        "label": "Các đơn vị trong công ty thực hiện được ý tưởng",
        "tooltip": None,
        "note": None,
        "score": 3,
        "input_type": "checkbox",
        "sort_order": 1,
    },
    {
        "criterion_key": "K2_EASY",
        "code": "B2",
        "label": "Thời gian triển khai nhanh, đơn giản (<= 2 ngày)",
        "tooltip": None,
        "note": None,
        "score": 3,
        "input_type": "checkbox",
        "sort_order": 2,
    },
    {
        "criterion_key": "K2_EASY",
        "code": "B3",
        "label": "Dễ đưa vào sản xuất, công nhân dễ thao tác, làm quen dụng cụ nhanh",
        "tooltip": None,
        "note": "Có thể làm thành thạo trong 1 ngày.",
        "score": 3,
        "input_type": "checkbox",
        "sort_order": 3,
    },
    {
        "criterion_key": "K2_HARD",
        "code": "B4",
        "label": "Cần gia công bên ngoài, trong công ty không thực hiện được ý tưởng",
        "tooltip": None,
        "note": None,
        "score": 2,
        "input_type": "checkbox",
        "sort_order": 1,
    },
    {
        "criterion_key": "K2_HARD",
        "code": "B5",
        "label": "Thời gian triển khai ý tưởng lâu (> 2 ngày)",
        "tooltip": None,
        "note": None,
        "score": 2,
        "input_type": "checkbox",
        "sort_order": 2,
    },
    {
        "criterion_key": "K2_HARD",
        "code": "B6",
        "label": "Công nhân mất nhiều thời gian để làm quen công việc, dụng cụ",
        "tooltip": None,
        "note": "Có thể làm thành thạo trong thời gian > 1 ngày.",
        "score": 2,
        "input_type": "checkbox",
        "sort_order": 3,
    },
    {
        "criterion_key": "K3_TIME_SAVED",
        "code": "C1",
        "label": "80 - 100%",
        "tooltip": "Tiết kiệm thời gian so với cũ.",
        "note": None,
        "score": 60,
        "input_type": "select",
        "sort_order": 1,
    },
    {
        "criterion_key": "K3_TIME_SAVED",
        "code": "C2",
        "label": "60 - 80%",
        "tooltip": "Tiết kiệm thời gian so với cũ.",
        "note": None,
        "score": 40,
        "input_type": "select",
        "sort_order": 2,
    },
    {
        "criterion_key": "K3_TIME_SAVED",
        "code": "C3",
        "label": "40 - 60%",
        "tooltip": "Tiết kiệm thời gian so với cũ.",
        "note": None,
        "score": 20,
        "input_type": "select",
        "sort_order": 3,
    },
    {
        "criterion_key": "K3_TIME_SAVED",
        "code": "C4",
        "label": "20 - 40%",
        "tooltip": "Tiết kiệm thời gian so với cũ.",
        "note": None,
        "score": 10,
        "input_type": "select",
        "sort_order": 4,
    },
    {
        "criterion_key": "K3_TIME_SAVED",
        "code": "C5",
        "label": "Dưới 10%",
        "tooltip": "Tiết kiệm thời gian so với cũ.",
        "note": None,
        "score": 5,
        "input_type": "select",
        "sort_order": 5,
    },
    {
        "criterion_key": "K3_COST_SAVED",
        "code": "C1",
        "label": "Trên 10.000.000 VND",
        "tooltip": "Tiết kiệm chi phí trực tiếp.",
        "note": "Tạm seed theo bộ tiêu chí không phải số hoá trước đây để hệ thống chạy thống nhất.",
        "score": 100,
        "input_type": "select",
        "sort_order": 1,
    },
    {
        "criterion_key": "K3_COST_SAVED",
        "code": "C2",
        "label": "5.000.000 - 10.000.000 VND",
        "tooltip": "Tiết kiệm chi phí trực tiếp.",
        "note": None,
        "score": 60,
        "input_type": "select",
        "sort_order": 2,
    },
    {
        "criterion_key": "K3_COST_SAVED",
        "code": "C3",
        "label": "3.000.000 - 5.000.000 VND",
        "tooltip": "Tiết kiệm chi phí trực tiếp.",
        "note": None,
        "score": 40,
        "input_type": "select",
        "sort_order": 3,
    },
    {
        "criterion_key": "K3_COST_SAVED",
        "code": "C4",
        "label": "1.500.000 - 3.000.000 VND",
        "tooltip": "Tiết kiệm chi phí trực tiếp.",
        "note": None,
        "score": 20,
        "input_type": "select",
        "sort_order": 4,
    },
    {
        "criterion_key": "K3_COST_SAVED",
        "code": "C5",
        "label": "Dưới 1.500.000 VND",
        "tooltip": "Tiết kiệm chi phí trực tiếp.",
        "note": None,
        "score": 10,
        "input_type": "select",
        "sort_order": 5,
    },
    {
        "criterion_key": "K3_UNMEASURABLE",
        "code": "C11",
        "label": "Cải thiện đường chuyền, giúp cân bằng chuyền, giảm vốn tồn",
        "tooltip": None,
        "note": None,
        "score": 10,
        "input_type": "checkbox",
        "sort_order": 1,
    },
    {
        "criterion_key": "K3_UNMEASURABLE",
        "code": "C12",
        "label": "Đơn giản hóa công việc, giảm chồng chéo/lặp lại, rút ngắn thời gian làm việc, tăng hiệu suất",
        "tooltip": None,
        "note": None,
        "score": 10,
        "input_type": "checkbox",
        "sort_order": 2,
    },
    {
        "criterion_key": "K3_UNMEASURABLE",
        "code": "C13",
        "label": "Tăng chất lượng, hạn chế sự cố/sai sót",
        "tooltip": None,
        "note": None,
        "score": 10,
        "input_type": "checkbox",
        "sort_order": 3,
    },
    {
        "criterion_key": "K3_UNMEASURABLE",
        "code": "C14",
        "label": "Cải thiện khu vực sản xuất an toàn, thông thoáng",
        "tooltip": None,
        "note": None,
        "score": 10,
        "input_type": "checkbox",
        "sort_order": 4,
    },
]


def seed_units() -> int:
    """
    Insert seed units if missing.
    Safe to run multiple times; matches on Unit.name.
    """
    db = SessionLocal()
    try:
        existing_by_name: dict[str, Unit] = {u.name: u for u in db.query(Unit).all()}
        inserted = 0

        for item in UNITS_SEED:
            name = item["name"]
            department = item["department"]

            unit = existing_by_name.get(name)
            if unit is None:
                db.add(Unit(name=name, department=department))
                inserted += 1
                continue

            if (unit.department is None or unit.department.strip() == "") and department:
                unit.department = department

        if inserted:
            db.commit()
        else:
            db.flush()

        return inserted
    finally:
        db.close()


def migrate_user_role_column() -> None:
    """
    Older versions stored users.role as a Postgres enum with values like 'ADMIN'.
    This app now stores roles as plain text using lowercase snake_case.
    """
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT data_type, udt_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'users'
                  AND column_name = 'role'
                """
            )
        ).fetchone()
        if not row:
            return

        data_type, udt_name = row
        if data_type == "USER-DEFINED":
            conn.execute(text("ALTER TABLE public.users ALTER COLUMN role TYPE text USING role::text"))

        # Map legacy uppercase enum values (if any) -> new roles
        conn.execute(
            text(
                """
                UPDATE public.users
                SET role = CASE role
                    WHEN 'ADMIN' THEN 'admin'
                    WHEN 'EMPLOYEE' THEN 'employee'
                    WHEN 'UNIT_MANAGER' THEN 'dept_manager'
                    WHEN 'DEPT_HEAD' THEN 'dept_manager'
                    WHEN 'INNOVATION_COUNCIL' THEN 'ie_manager'
                    WHEN 'LEADERSHIP' THEN 'bod_manager'
                    WHEN 'REVIEWER' THEN 'dept_manager'
                    ELSE role
                END
                """
            )
        )
        conn.execute(text("ALTER TABLE public.users ALTER COLUMN role SET DEFAULT 'employee'"))


def normalize_employee_codes() -> None:
    """
    Normalize employee_code to uppercase for consistent lookups.
    """
    with engine.begin() as conn:
        conn.execute(text("UPDATE public.users SET employee_code = upper(employee_code)"))


def migrate_idea_participants_column() -> None:
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'ideas'
                  AND column_name = 'participants_json'
                """
            )
        ).fetchone()
        if row:
            return

        conn.execute(text("ALTER TABLE public.ideas ADD COLUMN participants_json text"))


def migrate_idea_bo_phan_column() -> None:
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'ideas'
                  AND column_name = 'bo_phan'
                """
            )
        ).fetchone()
        if row:
            return

        conn.execute(text("ALTER TABLE public.ideas ADD COLUMN bo_phan varchar(255)"))


def migrate_idea_category_column() -> None:
    """
    Convert ideas.category to text so category options can evolve without
    Postgres enum migrations, then normalize legacy values.
    """
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'ideas'
                  AND column_name = 'category'
                """
            )
        ).fetchone()
        if not row:
            return

        if row[0] == "USER-DEFINED":
            conn.execute(text("ALTER TABLE public.ideas ALTER COLUMN category TYPE text USING category::text"))

        conn.execute(
            text(
                """
                UPDATE public.ideas
                SET category = CASE category
                    WHEN 'EQUIPMENT' THEN 'TOOLS'
                    WHEN 'PROCESS' THEN 'PROCESS'
                    WHEN 'QUALITY' THEN 'PROCESS'
                    WHEN 'SAFETY' THEN 'PROCESS'
                    WHEN 'COST' THEN 'PROCESS'
                    WHEN 'HR' THEN 'PROCESS'
                    WHEN 'ENVIRONMENT' THEN 'OTHER'
                    WHEN 'DIGITIZATION' THEN 'DIGITIZATION'
                    WHEN 'OTHER' THEN 'OTHER'
                    ELSE category
                END
                """
            )
        )


def migrate_score_k2_type_column() -> None:
    """
    Convert idea_scores.k2_type to text and normalize old values.
    """
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'idea_scores'
                  AND column_name = 'k2_type'
                """
            )
        ).fetchone()
        if not row:
            return

        if row[0] == "USER-DEFINED":
            conn.execute(text("ALTER TABLE public.idea_scores ALTER COLUMN k2_type TYPE text USING k2_type::text"))

        conn.execute(
            text(
                """
                UPDATE public.idea_scores
                SET k2_type = CASE k2_type
                    WHEN 'B1' THEN 'DIGITAL_SELF_DEVELOPED'
                    WHEN 'B2' THEN 'DIGITAL_CO_DEVELOPED'
                    WHEN 'B3' THEN 'DIGITAL_OUTSOURCE'
                    ELSE k2_type
                END
                """
            )
        )


def normalize_sample_idea_categories() -> None:
    """
    Existing sample ideas are intended to be Số hoá.
    """
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE public.ideas
                SET category = 'DIGITIZATION'
                WHERE id IN (3, 4)
                """
            )
        )


def migrate_score_criteria_tables() -> None:
    with engine.begin() as conn:
        columns = {
            "k2_selected_codes": "ALTER TABLE public.idea_scores ADD COLUMN k2_selected_codes text",
            "k3_option_code": "ALTER TABLE public.idea_scores ADD COLUMN k3_option_code varchar(20)",
            "k3_selected_codes": "ALTER TABLE public.idea_scores ADD COLUMN k3_selected_codes text",
        }
        existing = {
            row[0]
            for row in conn.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'idea_scores'
                    """
                )
            ).fetchall()
        }
        for name, ddl in columns.items():
            if name not in existing:
                conn.execute(text(ddl))

        conn.execute(
            text(
                """
                UPDATE public.idea_scores
                SET k2_type = CASE
                    WHEN k2_type IN ('NORMAL_EASY', 'DIGITAL_SELF_DEVELOPED', 'DIGITAL_CO_DEVELOPED') THEN 'EASY'
                    WHEN k2_type IN ('NORMAL_HARD', 'DIGITAL_OUTSOURCE') THEN 'HARD'
                    ELSE k2_type
                END
                WHERE k2_type IS NOT NULL
                """
            )
        )

        review_columns = {
            "recommend_unit_reward": "ALTER TABLE public.idea_reviews ADD COLUMN recommend_unit_reward boolean NOT NULL DEFAULT false",
        }
        existing_review_cols = {
            row[0]
            for row in conn.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'idea_reviews'
                    """
                )
            ).fetchall()
        }
        for name, ddl in review_columns.items():
            if name not in existing_review_cols:
                conn.execute(text(ddl))

        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS public.actual_benefit_evaluations (
                    id serial PRIMARY KEY,
                    idea_id integer NOT NULL UNIQUE REFERENCES public.ideas(id) ON DELETE CASCADE,
                    evaluator_id integer NOT NULL REFERENCES public.users(id),
                    before_seconds double precision NOT NULL,
                    after_seconds double precision NOT NULL,
                    improvement_percent double precision NOT NULL,
                    quantity integer NOT NULL,
                    labor_second_price double precision NOT NULL DEFAULT 6.14,
                    benefit_value double precision NOT NULL,
                    note text,
                    evaluated_at timestamp with time zone DEFAULT now(),
                    updated_at timestamp with time zone
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_actual_benefit_evaluations_idea_id
                ON public.actual_benefit_evaluations (idea_id)
                """
            )
        )

        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS public.score_criteria_sets (
                    id serial PRIMARY KEY,
                    name varchar(255) NOT NULL,
                    effective_from date NOT NULL,
                    created_by varchar(50),
                    created_at timestamp with time zone DEFAULT now(),
                    updated_at timestamp with time zone
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_score_criteria_sets_effective_from
                ON public.score_criteria_sets (effective_from)
                """
            )
        )

        existing_score_cols = {
            row[0]
            for row in conn.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'score_criteria'
                    """
                )
            ).fetchall()
        }
        if "criteria_set_id" not in existing_score_cols:
            conn.execute(text("ALTER TABLE public.score_criteria ADD COLUMN criteria_set_id integer"))

        has_fk = conn.execute(
            text(
                """
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'fk_score_criteria_criteria_set_id'
                """
            )
        ).fetchone()
        if not has_fk:
            conn.execute(
                text(
                    """
                    ALTER TABLE public.score_criteria
                    ADD CONSTRAINT fk_score_criteria_criteria_set_id
                    FOREIGN KEY (criteria_set_id) REFERENCES public.score_criteria_sets(id)
                    """
                )
            )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_score_criteria_criteria_set_id
                ON public.score_criteria (criteria_set_id)
                """
            )
        )

    default_set_id = None
    with engine.begin() as conn:
        default_set_id = conn.execute(
            text(
                """
                SELECT id
                FROM public.score_criteria_sets
                ORDER BY effective_from ASC, id ASC
                LIMIT 1
                """
            )
        ).scalar()
        if default_set_id is None:
            default_set_id = conn.execute(
                text(
                    """
                    INSERT INTO public.score_criteria_sets (name, effective_from, created_by)
                    VALUES ('Bo tieu chi mac dinh', CURRENT_DATE, 'seed')
                    RETURNING id
                    """
                )
            ).scalar()
        conn.execute(
            text(
                """
                UPDATE public.score_criteria
                SET criteria_set_id = :criteria_set_id
                WHERE criteria_set_id IS NULL
                """
            ),
            {"criteria_set_id": default_set_id},
        )


def migrate_payment_slip_reward_columns() -> None:
    with engine.begin() as conn:
        existing = {
            row[0]
            for row in conn.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'payment_slips'
                    """
                )
            ).fetchall()
        }

        if "paid_by_user_id" not in existing:
            conn.execute(text("ALTER TABLE public.payment_slips ADD COLUMN paid_by_user_id integer REFERENCES public.users(id)"))
        if "paid_at" not in existing:
            conn.execute(text("ALTER TABLE public.payment_slips ADD COLUMN paid_at timestamp with time zone"))


def migrate_reward_batch_special_coefficients_column() -> None:
    inspector = inspect(engine)
    if not inspector.has_table("reward_batches"):
        return

    existing = {column["name"] for column in inspector.get_columns("reward_batches")}
    if "special_coefficients" in existing:
        return

    table_name = "public.reward_batches" if engine.dialect.name == "postgresql" else "reward_batches"
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN special_coefficients text"))


def migrate_file_attachments_drive_columns() -> None:
    inspector = inspect(engine)
    if not inspector.has_table("file_attachments"):
        return

    existing = {column["name"] for column in inspector.get_columns("file_attachments")}
    table_name = "public.file_attachments" if engine.dialect.name == "postgresql" else "file_attachments"
    statements = {
        "storage_provider": f"ALTER TABLE {table_name} ADD COLUMN storage_provider varchar(50) NOT NULL DEFAULT 'local'",
        "external_file_id": f"ALTER TABLE {table_name} ADD COLUMN external_file_id varchar(255)",
        "external_folder_id": f"ALTER TABLE {table_name} ADD COLUMN external_folder_id varchar(255)",
        "external_url": f"ALTER TABLE {table_name} ADD COLUMN external_url varchar(500)",
        "mime_type": f"ALTER TABLE {table_name} ADD COLUMN mime_type varchar(255)",
    }

    with engine.begin() as conn:
        for column_name, ddl in statements.items():
            if column_name not in existing:
                conn.execute(text(ddl))


def seed_score_criteria() -> int:
    db = SessionLocal()
    try:
        criteria_set = (
            db.query(ScoreCriteriaSet)
            .order_by(ScoreCriteriaSet.effective_from.asc(), ScoreCriteriaSet.id.asc())
            .first()
        )
        if criteria_set is None:
            criteria_set = ScoreCriteriaSet(
                name="Bộ tiêu chí mặc định",
                effective_from=date.today(),
                created_by="seed",
            )
            db.add(criteria_set)
            db.commit()
            db.refresh(criteria_set)

        orphan_rows = db.query(ScoreCriteria).filter(ScoreCriteria.criteria_set_id.is_(None)).all()
        for row in orphan_rows:
            row.criteria_set_id = criteria_set.id
            db.add(row)
        if orphan_rows:
            db.commit()

        existing = {
            (item.criteria_set_id, item.criterion_key, item.code): item
            for item in db.query(ScoreCriteria).all()
        }
        inserted = 0

        for item in SCORE_CRITERIA_SEED:
            key = (criteria_set.id, str(item["criterion_key"]), str(item["code"]))
            row = existing.get(key)
            if row is None:
                db.add(ScoreCriteria(criteria_set_id=criteria_set.id, **item))
                inserted += 1
                continue

            changed = False
            for field in ("label", "tooltip", "note", "score", "input_type", "sort_order", "is_active"):
                new_value = item.get(field, True if field == "is_active" else None)
                if getattr(row, field) != new_value:
                    setattr(row, field, new_value)
                    changed = True
            if changed:
                db.add(row)

        db.commit()
        return inserted
    finally:
        db.close()


def migrate_users_unit_nullable() -> None:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE public.users ALTER COLUMN unit_id DROP NOT NULL"))


def seed_admin_user() -> bool:
    """
    Ensure a default admin user exists:
    employee_code=admin, full_name=admin, role=ADMIN
    """
    db = SessionLocal()
    try:
        unit = db.query(Unit).filter(Unit.name == "P. Tổng hợp").first()
        if unit is None:
            unit = Unit(name="P. Tổng hợp", department="Phòng ban")
            db.add(unit)
            db.commit()
            db.refresh(unit)

        user = db.query(User).filter(User.employee_code == "ADMIN").first()
        if user is None:
            db.add(
                User(
                    employee_code="ADMIN",
                    full_name="admin",
                    role=UserRole.ADMIN.value,
                    unit_id=unit.id,
                    is_active=True,
                )
            )
            db.commit()
            return True

        changed = False
        if user.full_name != "admin":
            user.full_name = "admin"
            changed = True
        if user.role != UserRole.ADMIN.value:
            user.role = UserRole.ADMIN.value
            changed = True
        if user.unit_id != unit.id:
            user.unit_id = unit.id
            changed = True
        if user.is_active is not True:
            user.is_active = True
            changed = True

        if changed:
            db.commit()
        return False
    finally:
        db.close()
