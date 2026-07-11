import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, CheckConstraint, UniqueConstraint, Integer, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from .database import Base

class Admin(Base):
    __tablename__ = "admins"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    ranking_published = Column(Boolean, default=False)

class Poll(Base):
    __tablename__ = "polls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=True)
    order_index = Column(Integer, default=0)
    question = Column(String, nullable=False)
    option_a_text = Column(String, nullable=False)
    option_b_text = Column(String, nullable=False)
    status = Column(String, default="draft", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)
    winner_option = Column(String(1), nullable=True)
    final_counts = Column(JSONB, nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('draft', 'active', 'closed')", name="status_check"),
    )

class Participant(Base):
    __tablename__ = "participants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    poll_id = Column(UUID(as_uuid=True), ForeignKey("polls.id"))
    name = Column(String, nullable=False)
    has_voted = Column(Boolean, default=False)
    voted_option = Column(String(1), nullable=True)
    voted_at = Column(DateTime(timezone=True), nullable=True)
    last_vote_attempt_id = Column(String, nullable=True)
    device_token = Column(String, nullable=True)

    __table_args__ = (
        CheckConstraint("voted_option IN ('A', 'B')", name="voted_option_check"),
        UniqueConstraint("poll_id", "name", name="uq_poll_participant"),
        Index("ix_participants_poll_status", "poll_id", "has_voted"),
        Index("ix_participants_poll_device", "poll_id", "device_token"),
    )

class VoteEvent(Base):
    __tablename__ = "vote_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    poll_id = Column(UUID(as_uuid=True), ForeignKey("polls.id"))
    option = Column(String(1), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("option IN ('A', 'B')", name="vote_event_option_check"),
        Index("ix_vote_events_poll_time", "poll_id", "created_at"),
    )

class AdminAuditLog(Base):
    __tablename__ = "admin_audit_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admin_id = Column(UUID(as_uuid=True), ForeignKey("admins.id"))
    action = Column(String, nullable=False)
    poll_id = Column(UUID(as_uuid=True), ForeignKey("polls.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

