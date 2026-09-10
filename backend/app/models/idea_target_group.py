from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey, ForeignKeyConstraint, UniqueConstraint, CheckConstraint
from sqlalchemy.sql import func
from app.database import Base


class IdeaTargetGroup(Base):
    __tablename__ = "idea_target_groups"
    __table_args__ = (
        UniqueConstraint("year", "name"), UniqueConstraint("year", "id"),
        CheckConstraint("year BETWEEN 2000 AND 2100"),
        CheckConstraint("target_count >= 0"), CheckConstraint("headcount >= 0"),
        CheckConstraint("target_percent >= 0 AND target_percent <= 100"),
    )
    id = Column(Integer, primary_key=True)
    year = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    target_count = Column(Integer, nullable=False)
    headcount = Column(Integer)
    target_percent = Column(Numeric(5, 2))
    updated_by = Column(String(50))
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class IdeaTargetGroupMember(Base):
    __tablename__ = "idea_target_group_members"
    __table_args__ = (ForeignKeyConstraint(["year", "group_id"], ["idea_target_groups.year", "idea_target_groups.id"], ondelete="CASCADE"),)
    year = Column(Integer, primary_key=True)
    unit_id = Column(Integer, ForeignKey("units.id"), primary_key=True)
    group_id = Column(Integer, nullable=False)


class IdeaTargetExcludedUnit(Base):
    __tablename__ = "idea_target_excluded_units"
    year = Column(Integer, primary_key=True)
    unit_id = Column(Integer, ForeignKey("units.id"), primary_key=True)
    reason = Column(String(255), nullable=False)
