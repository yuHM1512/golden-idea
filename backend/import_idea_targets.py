"""Preview by default; --apply backs up and replaces only the specified target year.

Uses DATABASE_URL from the environment or the backend .env. Never prints credentials.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import inspect
from sqlalchemy.orm import Session
from app.database import engine
from app.models import Unit, UnitIdeaTarget
from app.models.idea_target_group import IdeaTargetGroup, IdeaTargetGroupMember, IdeaTargetExcludedUnit
from app.services.idea_targets import list_groups, migrate_target_groups


def resolve_import(db, source):
    by_name = {u.name: u.id for u in db.query(Unit).all()}
    names = [n for g in source["groups"] for n in g["units"]] + source["excluded_units"]
    missing = sorted(set(names) - set(by_name))
    if missing:
        raise ValueError(f"Unmapped units: {missing}")
    if len(names) != len(set(names)):
        raise ValueError("Duplicate unit membership")
    if sum(g["headcount"] for g in source["groups"]) != source["expected_headcount"]:
        raise ValueError("Headcount total mismatch")
    if sum(g["target_count"] for g in source["groups"]) != source["expected_target_count"]:
        raise ValueError("Target total mismatch")
    return by_name


def apply_import(db, source):
    by_name = resolve_import(db, source)
    year = source["year"]
    db.query(IdeaTargetGroupMember).filter_by(year=year).delete(synchronize_session=False)
    db.query(IdeaTargetGroup).filter_by(year=year).delete(synchronize_session=False)
    db.query(IdeaTargetExcludedUnit).filter_by(year=year).delete(synchronize_session=False)
    db.query(UnitIdeaTarget).filter_by(year=year).delete(synchronize_session=False)
    for item in source["groups"]:
        group = IdeaTargetGroup(year=year, name=item["name"], target_count=item["target_count"],
                                headcount=item["headcount"], target_percent=item["target_percent"], updated_by="IMPORT_2026")
        db.add(group)
        db.flush()
        db.add_all([IdeaTargetGroupMember(year=year, unit_id=by_name[n], group_id=group.id) for n in item["units"]])
    db.add_all([IdeaTargetExcludedUnit(year=year, unit_id=by_name[n], reason="Ngừng hoạt động") for n in source["excluded_units"]])
    db.flush()
    groups = list_groups(db, year)
    assert len(groups) == 14 and sum(g["target_count"] for g in groups) == source["expected_target_count"]
    return groups


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup-dir", type=Path, default=Path(__file__).parent / "data" / "target_backups")
    args = parser.parse_args()
    source = json.loads((Path(__file__).parent / "data" / "idea_targets_2026.json").read_text(encoding="utf-8"))
    with Session(engine) as db:
        mapping = resolve_import(db, source)
        print(json.dumps({"host": engine.url.host, "database": engine.url.database, "year": source["year"],
                          "groups": len(source["groups"]), "target_count": source["expected_target_count"],
                          "headcount": source["expected_headcount"], "mapped_units": len(mapping)}, ensure_ascii=True))
        tables = set(inspect(engine).get_table_names())
        backup = {"year": source["year"], "legacy": [], "groups": [], "exclusions": []}
        if "unit_idea_targets" in tables:
            backup["legacy"] = [{"unit_id": r.unit_id, "target_count": r.target_count, "updated_by": r.updated_by}
                                for r in db.query(UnitIdeaTarget).filter_by(year=source["year"]).all()]
        if "idea_target_groups" in tables:
            backup["groups"] = list_groups(db, source["year"])
            backup["exclusions"] = [{"unit_id": r.unit_id, "reason": r.reason} for r in db.query(IdeaTargetExcludedUnit).filter_by(year=source["year"]).all()]
        print(json.dumps({"existing_groups": len(backup["groups"]), "existing_legacy": len(backup["legacy"]), "apply": args.apply}))
    if not args.apply:
        return
    args.backup_dir.mkdir(parents=True, exist_ok=True)
    path = args.backup_dir / ("targets_2026_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
    path.write_text(json.dumps(backup, ensure_ascii=False, indent=2), encoding="utf-8")
    UnitIdeaTarget.__table__.create(engine, checkfirst=True)
    migrate_target_groups(engine)
    with Session(engine) as db, db.begin():
        apply_import(db, source)
    print(f"Imported 14 groups, 123 targets. Backup: {path}")


if __name__ == "__main__":
    main()
