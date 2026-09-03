from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CaseCreate(BaseModel):
    case_id: str = Field(min_length=4, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    title: str = Field(min_length=3, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)


class CaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: str
    title: str
    description: Optional[str]
    status: str
    created_by_user_id: int
    created_at: datetime


class CaseWorkspace(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    case: CaseRead
    role: str
    access_status: Optional[str] = None
    message: Optional[str] = None


class MyCase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: str
    title: str
    description: Optional[str]
    status: str
    created_by_user_id: int
    created_at: datetime
    access_status: Optional[str] = None
    role: str = "INVESTIGATOR"