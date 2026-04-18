from __future__ import annotations
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class Position(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    report_to: Optional[str] = None
    headcount: Optional[int] = None
    location: Optional[str] = None
    start_date: Optional[str] = None


class HardRequirements(BaseModel):
    education: Optional[str] = None
    years: Optional[str] = None
    skills: list[str] = Field(default_factory=list)
    industry: Optional[str] = None


class SoftPreferences(BaseModel):
    bonus_points: list[str] = Field(default_factory=list)
    culture_fit: Optional[str] = None
    team_style: Optional[str] = None


class Compensation(BaseModel):
    salary_range: Optional[str] = None
    level: Optional[str] = None
    employment_type: Optional[str] = None


class Profile(BaseModel):
    position: Position = Field(default_factory=Position)
    responsibilities: list[str] = Field(default_factory=list)
    hard_requirements: HardRequirements = Field(default_factory=HardRequirements)
    soft_preferences: SoftPreferences = Field(default_factory=SoftPreferences)
    compensation: Compensation = Field(default_factory=Compensation)


Status = Literal["drafting", "pending_review", "approved"]


class MessageRead(BaseModel):
    id: UUID
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class JDRead(BaseModel):
    content_md: str
    edited_content_md: Optional[str] = None
    generated_at: datetime
    approved_at: Optional[datetime] = None


class RequestRead(BaseModel):
    id: UUID
    title: str
    status: Status
    profile: dict
    missing_fields: list[str]
    ready_for_jd: bool
    messages: list[MessageRead] = Field(default_factory=list)
    jd: Optional[JDRead] = None
    created_at: datetime
    updated_at: datetime


class RequestListItem(BaseModel):
    id: UUID
    title: str
    status: Status
    updated_at: datetime


class PostMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)


class PostMessageResponse(BaseModel):
    assistant_message: MessageRead
    profile: dict
    missing_fields: list[str]
    ready_for_jd: bool


class PatchRequestBody(BaseModel):
    edited_content_md: Optional[str] = None
    action: Optional[Literal["approve"]] = None
