from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class K1Type(str, Enum):
    COMPLETELY_NEW = "A1"
    IMPROVEMENT = "A2"
    OLD = "A3"


class K2Type(str, Enum):
    EASY = "EASY"
    HARD = "HARD"
    NORMAL_EASY = "NORMAL_EASY"
    NORMAL_HARD = "NORMAL_HARD"
    DIGITAL_SELF_DEVELOPED = "DIGITAL_SELF_DEVELOPED"
    DIGITAL_CO_DEVELOPED = "DIGITAL_CO_DEVELOPED"
    DIGITAL_OUTSOURCE = "DIGITAL_OUTSOURCE"


class K3MeasureType(str, Enum):
    TIME_SAVED = "TIME_SAVED"
    COST_SAVED = "COST_SAVED"
    UNMEASURABLE = "UNMEASURABLE"


class IdeaScoreCreate(BaseModel):
    idea_id: int
    k1_type: K1Type = Field(...)
    k1_note: Optional[str] = None
    k2_type: str = Field(...)
    k2_selected_codes: list[str] = Field(default_factory=list)
    k2_note: Optional[str] = None
    k3_measure_type: K3MeasureType = Field(...)
    k3_option_code: Optional[str] = None
    k3_selected_codes: list[str] = Field(default_factory=list)
    k3_value: Optional[float] = None
    k3_note: Optional[str] = None


class IdeaScoreResponse(BaseModel):
    id: int
    idea_id: int
    scorer_id: int
    k1_type: str
    k1_score: int
    k1_note: Optional[str]
    k2_type: str
    k2_score: int
    k2_selected_codes: list[str] = Field(default_factory=list)
    k2_time_frame: Optional[str]
    k2_note: Optional[str]
    k3_measure_type: str
    k3_option_code: Optional[str]
    k3_selected_codes: list[str] = Field(default_factory=list)
    k3_score: int
    k3_value: Optional[float]
    k3_note: Optional[str]
    total_score: int
    is_final: bool
    scored_at: datetime

    class Config:
        from_attributes = True


class K1ScoreBreakdown(BaseModel):
    A1: int = 10
    A2: int = 5
    A3: int = 2


class K2ScoreBreakdown(BaseModel):
    EASY_MAX: int = 9
    HARD_MAX: int = 6


class K3ScoreGuide(BaseModel):
    MEASURABLE_MAX: int = 60
    UNMEASURABLE_EACH: int = 10


class ScoreCriteriaItemInput(BaseModel):
    criterion_key: str
    code: str
    label: str
    tooltip: Optional[str] = None
    note: Optional[str] = None
    score: int = Field(default=0)
    input_type: str = Field(default="radio")
    sort_order: int = Field(default=0)
    is_active: bool = Field(default=True)


class ScoreCriteriaSetCreate(BaseModel):
    employee_code: str
    effective_from: date
    name: Optional[str] = None
    items: list[ScoreCriteriaItemInput] = Field(default_factory=list)


class ScoreCriteriaSetUpdate(BaseModel):
    employee_code: str
    effective_from: date
    name: Optional[str] = None
    items: list[ScoreCriteriaItemInput] = Field(default_factory=list)


class ScoreCriteriaItemResponse(ScoreCriteriaItemInput):
    id: int
    criteria_set_id: Optional[int] = None

    class Config:
        from_attributes = True


class ScoreCriteriaSetResponse(BaseModel):
    id: int
    name: str
    effective_from: date
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    items: list[ScoreCriteriaItemResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True
