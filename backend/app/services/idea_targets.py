from fastapi import HTTPException
from sqlalchemy import select, text
from app.models.idea_target_group import IdeaTargetGroup, IdeaTargetGroupMember, IdeaTargetExcludedUnit
from app.models.unit import Unit
from app.models.unit_idea_target import UnitIdeaTarget


def migrate_target_groups(engine):
    """Create tables and copy legacy targets once, without replacing edited groups."""
    from sqlalchemy.orm import Session
    for model in (IdeaTargetGroup, IdeaTargetGroupMember, IdeaTargetExcludedUnit):
        model.__table__.create(engine, checkfirst=True)
    with Session(engine) as db, db.begin():
        for old in db.query(UnitIdeaTarget).all():
            if db.get(IdeaTargetGroupMember, (old.year, old.unit_id)) or db.get(IdeaTargetExcludedUnit, (old.year, old.unit_id)):
                continue
            unit = db.get(Unit, old.unit_id)
            group = IdeaTargetGroup(year=old.year, name=unit.name, target_count=old.target_count, updated_by=old.updated_by)
            db.add(group)
            db.flush()
            db.add(IdeaTargetGroupMember(year=old.year, unit_id=old.unit_id, group_id=group.id))
    create_idea_kpi_view(engine)


def create_idea_kpi_view(engine):
    """Create the replacement data source for KPI 222.

    Approved totals for 2025 are a fixed historical snapshot. From 2026 onward
    the view follows the live dashboard rule: APPROVED + REWARDED, grouped by
    the year of submitted_at.
    """
    if engine.dialect.name != "postgresql":
        return

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE OR REPLACE VIEW public.idea_kpi_by_unit_year AS
                WITH approved_ideas AS (
                    SELECT
                        m.year,
                        m.group_id,
                        COUNT(i.id)::bigint AS ytv_duyet
                    FROM public.idea_target_group_members m
                    JOIN public.ideas i
                      ON i.unit_id = m.unit_id
                     AND EXTRACT(YEAR FROM i.submitted_at)::integer = m.year
                     AND i.status::text IN ('APPROVED', 'REWARDED')
                    GROUP BY m.year, m.group_id
                ),
                approved_2025(don_vi, ytv_duyet) AS (
                    VALUES
                        ('XN1-V1'::varchar, 16::bigint),
                        ('XN2'::varchar, 15::bigint),
                        ('XN3'::varchar, 15::bigint),
                        ('XNDT'::varchar, 32::bigint),
                        ('XNV2'::varchar, 5::bigint)
                )
                SELECT
                    ROW_NUMBER() OVER (ORDER BY g.year, g.name) AS stt,
                    g.year AS nam,
                    g.name AS don_vi,
                    g.target_count AS muc_tieu_ytv,
                    CASE
                        WHEN g.year = 2025 THEN COALESCE(h.ytv_duyet, 0::bigint)
                        ELSE COALESCE(a.ytv_duyet, 0::bigint)
                    END AS ytv_duyet
                FROM public.idea_target_groups g
                LEFT JOIN approved_ideas a
                  ON a.year = g.year
                 AND a.group_id = g.id
                LEFT JOIN approved_2025 h
                  ON g.year = 2025
                 AND h.don_vi = g.name
                """
            )
        )


def list_groups(db, year):
    members = db.query(IdeaTargetGroupMember).filter_by(year=year).all()
    return [{"id": g.id, "year": g.year, "name": g.name,
             "unit_ids": sorted(m.unit_id for m in members if m.group_id == g.id),
             "target_count": g.target_count, "headcount": g.headcount,
             "target_percent": float(g.target_percent) if g.target_percent is not None else None}
            for g in db.query(IdeaTargetGroup).filter_by(year=year).order_by(IdeaTargetGroup.id).all()]


def save_group(db, payload, actor):
    ids = sorted(set(payload.unit_ids or ([payload.unit_id] if payload.unit_id else [])))
    if not ids:
        raise HTTPException(422, "Chọn ít nhất một đơn vị")
    # Lock the member units in a stable order to serialize overlapping updates.
    units = db.execute(select(Unit).where(Unit.id.in_(ids)).order_by(Unit.id).with_for_update()).scalars().all()
    if len(units) != len(ids):
        raise HTTPException(404, "Đơn vị không tồn tại")
    if db.query(IdeaTargetExcludedUnit).filter(IdeaTargetExcludedUnit.year == payload.year, IdeaTargetExcludedUnit.unit_id.in_(ids)).first():
        raise HTTPException(409, "Đơn vị đã ngừng hoạt động trong năm này")
    group = db.get(IdeaTargetGroup, payload.group_id) if payload.group_id else None
    if payload.group_id and (group is None or group.year != payload.year):
        raise HTTPException(404, "Nhóm mục tiêu không tồn tại trong năm đã chọn")
    # Support the previous single-unit API without changing a multi-unit target.
    if not group and payload.unit_id and not payload.unit_ids:
        member = db.get(IdeaTargetGroupMember, (payload.year, payload.unit_id))
        if member:
            group = db.get(IdeaTargetGroup, member.group_id)
            if db.query(IdeaTargetGroupMember).filter_by(group_id=group.id).count() != 1:
                raise HTTPException(409, "Đơn vị thuộc nhóm gộp; hãy cập nhật mục tiêu của nhóm")
    name = (payload.name or (group.name if group else units[0].name)).strip()
    if not name:
        raise HTTPException(422, "Nhập tên nhóm mục tiêu")
    conflict = db.query(IdeaTargetGroupMember).filter(IdeaTargetGroupMember.year == payload.year, IdeaTargetGroupMember.unit_id.in_(ids))
    if group:
        conflict = conflict.filter(IdeaTargetGroupMember.group_id != group.id)
    if conflict.first():
        raise HTTPException(409, "Đơn vị đã thuộc nhóm mục tiêu khác trong năm này")
    duplicate = db.query(IdeaTargetGroup).filter_by(year=payload.year, name=name).first()
    if duplicate and (not group or duplicate.id != group.id):
        raise HTTPException(409, "Tên nhóm đã tồn tại trong năm này")
    if group is None:
        group = IdeaTargetGroup(year=payload.year)
        db.add(group)
    group.name, group.target_count = name, payload.target_count
    group.headcount, group.target_percent, group.updated_by = payload.headcount, payload.target_percent, actor
    db.flush()
    old_ids = [m.unit_id for m in db.query(IdeaTargetGroupMember).filter_by(group_id=group.id).all()]
    db.query(IdeaTargetGroupMember).filter_by(group_id=group.id).delete(synchronize_session="fetch")
    db.flush()
    db.add_all([IdeaTargetGroupMember(year=payload.year, unit_id=uid, group_id=group.id) for uid in ids])
    # Retire legacy records so startup migration cannot restore old memberships.
    db.query(UnitIdeaTarget).filter(UnitIdeaTarget.year == payload.year, UnitIdeaTarget.unit_id.in_(ids + old_ids)).delete(synchronize_session=False)
    db.flush()
    return group


def aggregate_targets(db, rows, year):
    if year is None:
        return [dict(row, target_count=None) for row in rows]
    excluded = {x.unit_id for x in db.query(IdeaTargetExcludedUnit).filter_by(year=year).all()}
    by_unit = {row["unit_id"]: row for row in rows if row["unit_id"] not in excluded}
    result, grouped = [], set()
    for g in list_groups(db, year):
        ids = [uid for uid in g["unit_ids"] if uid in by_unit]
        if not ids:
            continue
        grouped.update(ids)
        departments = {by_unit[uid]["department"] for uid in ids}
        result.append({"unit_id": ids[0] if len(ids) == 1 else None, "group_id": g["id"],
                       "unit_ids": ids, "unit_name": g["name"],
                       "department": next(iter(departments)) if len(departments) == 1 else "Liên đơn vị",
                       "idea_count": sum(by_unit[uid]["idea_count"] for uid in ids),
                       "target_count": g["target_count"]})
    result.extend(dict(row, target_count=None, unit_ids=[uid]) for uid, row in by_unit.items() if uid not in grouped)
    return result
