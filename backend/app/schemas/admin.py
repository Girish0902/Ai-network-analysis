from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AccessRequestOut(BaseModel):
    user_id: int
    username: str
    badge_number: str
    case_id: str
    status: str
    created_at: Optional[datetime] = None


class PendingRequestOut(AccessRequestOut):
    model_config = ConfigDict(from_attributes=True)


class AccessDecision(BaseModel):
    case_id: str
    user_id: int
    decision: str  # APPROVE | REJECT


class AccessDecisionOut(BaseModel):
    user_id: int
    case_id: str
    status: str
    message: str