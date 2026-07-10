from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime
from uuid import UUID

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class AdminLogin(BaseModel):
    username: str
    password: str

class ParticipantBase(BaseModel):
    name: str

class ParticipantCreate(ParticipantBase):
    pass

class ParticipantResponse(ParticipantBase):
    id: UUID
    poll_id: UUID
    has_voted: bool
    voted_option: Optional[str] = None
    voted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class ParticipantPublic(BaseModel):
    id: UUID
    name: str

    model_config = ConfigDict(from_attributes=True)

class ParticipantBulkCreate(BaseModel):
    names: List[str]

class SessionCreate(BaseModel):
    name: str

class SessionResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PollBase(BaseModel):
    question: str
    option_a_text: str
    option_b_text: str

class PollCreate(PollBase):
    pass

class PollUpdate(PollBase):
    pass

class PollResponse(PollBase):
    id: UUID
    session_id: Optional[UUID] = None
    order_index: int = 0
    status: str
    created_at: datetime
    closed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class VoteCreate(BaseModel):
    participant_id: UUID
    option: str

class PollResultOption(BaseModel):
    text: str
    count: int

class ParticipantStatus(BaseModel):
    name: str
    has_voted: bool

class PollResults(BaseModel):
    option_a: PollResultOption
    option_b: PollResultOption
    total: int
    participants: List[ParticipantStatus]

class ResetConfirm(BaseModel):
    confirm: bool

