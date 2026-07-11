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

class RosterBase(BaseModel):
    name: str

class RosterCreate(RosterBase):
    pass

class RosterResponse(RosterBase):
    id: UUID
    session_id: UUID
    vote_code: str

    model_config = ConfigDict(from_attributes=True)

class RoundVoteResponse(BaseModel):
    id: UUID
    poll_id: UUID
    roster_id: UUID
    has_voted: bool
    voted_option: Optional[str] = None
    voted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class ParticipantPublic(BaseModel):
    id: UUID
    name: str

    model_config = ConfigDict(from_attributes=True)

class RosterBulkCreate(BaseModel):
    names: List[str]

class SessionCreate(BaseModel):
    name: str

class SessionResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    ranking_published: bool

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
    order_index: Optional[int] = 0
    status: str
    created_at: datetime
    closed_at: Optional[datetime] = None
    ranking_published: bool = False

    model_config = ConfigDict(from_attributes=True)

class VoteCreate(BaseModel):
    participant_id: UUID
    vote_code: str
    option: str
    vote_attempt_id: str

class PollResultOption(BaseModel):
    text: str
    count: int

class ParticipantStatus(BaseModel):
    name: str
    has_voted: bool
    vote_code: Optional[str] = None

class PollResults(BaseModel):
    option_a: PollResultOption
    option_b: PollResultOption
    total: int
    participants: List[ParticipantStatus]

class ResetConfirm(BaseModel):
    confirm: bool

class PublicPollResult(BaseModel):
    question: str
    option_a_text: str
    option_b_text: str
    status: str
    counts: dict
    winner_option: Optional[str] = None

class SessionLeaderboardEntry(BaseModel):
    poll_id: UUID
    question: str
    winner_option: Optional[str] = None
    counts: Optional[dict] = None

class VoteStatusResponse(BaseModel):
    already_voted: bool
    name: Optional[str] = None
    option: Optional[str] = None

class RankingPublishRequest(BaseModel):
    published: bool

class RoundRanking(BaseModel):
    poll_id: UUID
    question: str
    option_a_text: str
    option_b_text: str
    counts: dict
    percentages: dict
    participation: dict
    result_label: Optional[str] = None

class PublicSessionRankingResponse(BaseModel):
    published: bool
    rounds: Optional[List[RoundRanking]] = None
