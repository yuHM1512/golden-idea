from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from .score import K1Type, K3MeasureType


class ReviewLevel(str, Enum):
    TECHNICAL = "TECHNICAL"
    DEPT_HEAD = "DEPT_HEAD"
    COUNCIL = "COUNCIL"
    LEADERSHIP = "LEADERSHIP"


class ReviewAction(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REQUEST_INFO = "REQUEST_INFO"
    FORWARD = "FORWARD"


class ApprovalScoreInput(BaseModel):
    k1_type: K1Type
    k1_note: Optional[str] = None
    k2_type: str
    k2_selected_codes: List[str] = Field(default_factory=list)
    k2_note: Optional[str] = None
    k3_measure_type: K3MeasureType
    k3_option_code: Optional[str] = None
    k3_selected_codes: List[str] = Field(default_factory=list)
    k3_value: Optional[float] = None
    k3_note: Optional[str] = None


class ActualBenefitInput(BaseModel):
    employee_code: str
    before_seconds: float
    after_seconds: float
    quantity: int
    labor_second_price: float = 6.14
    note: Optional[str] = None


class ActualBenefitView(BaseModel):
    id: int
    idea_id: int
    evaluator_id: int
    evaluator_name: str
    before_seconds: float
    after_seconds: float
    improvement_percent: float
    quantity: int
    labor_second_price: float
    benefit_value: float
    note: Optional[str]
    evaluated_at: datetime


class ApprovalSubmitRequest(BaseModel):
    employee_code: str
    idea_id: int
    action: ReviewAction = ReviewAction.APPROVE
    comment: Optional[str] = None
    recommend_unit_reward: bool = False
    score: Optional[ApprovalScoreInput] = None


class ApprovalScoreView(BaseModel):
    id: int
    scorer_id: int
    scorer_name: str
    scorer_role: str
    k1_type: str
    k1_score: int
    k1_note: Optional[str]
    k2_type: str
    k2_score: int
    k2_selected_codes: List[str] = Field(default_factory=list)
    k2_time_frame: Optional[str]
    k2_note: Optional[str]
    k3_measure_type: str
    k3_option_code: Optional[str]
    k3_selected_codes: List[str] = Field(default_factory=list)
    k3_score: int
    k3_value: Optional[float]
    k3_note: Optional[str]
    total_score: int
    is_final: bool
    scored_at: datetime


class ApprovalReviewView(BaseModel):
    id: int
    reviewer_id: int
    reviewer_name: str
    reviewer_role: str
    level: str
    action: str
    comment: Optional[str]
    recommend_unit_reward: bool = False
    reviewed_at: datetime


class ApprovalAttachmentView(BaseModel):
    id: int
    original_filename: str
    file_type: str
    file_size: int
    file_url: str
    uploaded_at: Optional[datetime]


class ApprovalIdeaItem(BaseModel):
    id: int
    title: str
    full_name: str
    employee_code: Optional[str]
    unit_id: int
    unit_name: str
    unit_department: Optional[str]
    category: str
    status: str
    description: str
    submitted_at: datetime
    attachments_count: int
    rejection_reason: Optional[str]
    can_review: bool
    employee_received: bool = False
    dept_score: Optional["ApprovalScoreView"] = None
    ie_score: Optional["ApprovalScoreView"] = None
    latest_review: Optional["ApprovalReviewView"] = None


class ApprovalIdeaDetail(ApprovalIdeaItem):
    phone_number: Optional[str]
    position: Optional[str]
    product_code: Optional[str]
    is_anonymous: bool
    attachments: List[ApprovalAttachmentView] = Field(default_factory=list)
    reviews: List[ApprovalReviewView] = Field(default_factory=list)
    scores: List[ApprovalScoreView] = Field(default_factory=list)
    actual_benefit: Optional[ActualBenefitView] = None


class ApprovalMetrics(BaseModel):
    total: int
    approved: int
    pending: int
    rejected: int


class ApprovalQueueResponse(BaseModel):
    role: str
    unit_id: Optional[int]
    unit_name: Optional[str]
    metrics: ApprovalMetrics
    items: List[ApprovalIdeaItem]


class IdeaReviewCreate(BaseModel):
    idea_id: int
    action: ReviewAction = ReviewAction.APPROVE
    comment: Optional[str] = None


class IdeaReviewResponse(BaseModel):
    id: int
    idea_id: int
    reviewer_id: int
    level: ReviewLevel
    action: ReviewAction
    comment: Optional[str]
    reviewed_at: datetime

    class Config:
        from_attributes = True


class ReviewHistoryResponse(BaseModel):
    technical: Optional[IdeaReviewResponse] = None
    dept_head: Optional[IdeaReviewResponse] = None
    council: Optional[IdeaReviewResponse] = None
    leadership: Optional[IdeaReviewResponse] = None
