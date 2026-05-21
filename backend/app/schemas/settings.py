from pydantic import BaseModel


class AdminSettingsResponse(BaseModel):
    email_automation_enabled: bool


class EmailAutomationUpdateRequest(BaseModel):
    employee_code: str
    enabled: bool


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
