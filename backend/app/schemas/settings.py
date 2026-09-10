from pydantic import BaseModel, Field


class UnitIdeaTargetUpdateRequest(BaseModel):
    employee_code: str
    year: int = Field(ge=2000, le=2100)
    unit_id: int | None = Field(default=None, gt=0)
    unit_ids: list[int] = Field(default_factory=list)
    group_id: int | None = Field(default=None, gt=0)
    name: str | None = Field(default=None, max_length=255)
    headcount: int | None = Field(default=None, ge=0, le=2147483647)
    target_percent: float | None = Field(default=None, ge=0, le=100)
    target_count: int = Field(strict=True, ge=0, le=2147483647)


class IdeaCategoryOption(BaseModel):
    name: str
    requires_stage: bool = True


class IdeaTaxonomyResponse(BaseModel):
    categories: list[IdeaCategoryOption]
    stages: list[str]


class LaborSecondPriceSettingItem(BaseModel):
    year: int
    labor_second_price: float


class LaborSecondPriceSettingsResponse(BaseModel):
    items: list[LaborSecondPriceSettingItem]


class AdminSettingsResponse(BaseModel):
    email_automation_enabled: bool
    idea_taxonomy: IdeaTaxonomyResponse


class EmailAutomationUpdateRequest(BaseModel):
    employee_code: str
    enabled: bool


class IdeaTaxonomyUpdateRequest(BaseModel):
    employee_code: str
    categories: list[IdeaCategoryOption]
    stages: list[str]


class LaborSecondPriceSettingsUpdateRequest(BaseModel):
    employee_code: str
    items: list[LaborSecondPriceSettingItem]


class IdeaBulkDeleteRequest(BaseModel):
    employee_code: str
    idea_ids: list[int]


class IdeaHardDeleteResponse(BaseModel):
    idea_id: int
    deleted: bool
    removed_reward_batch_refs: int
    removed_google_drive_files: int
    removed_local_files: int
    cleanup_warnings: list[str]
