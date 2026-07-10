import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from .database import Base

class Admin(Base):
    __tablename__ = "admins"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Poll(Base):
    __tablename__ = "polls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question = Column(String, nullable=False)
    option_a_text = Column(String, nullable=False)
    option_b_text = Column(String, nullable=False)
    status = Column(String, default="draft", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)

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

    __table_args__ = (
        CheckConstraint("voted_option IN ('A', 'B')", name="voted_option_check"),
        UniqueConstraint("poll_id", "name", name="uq_poll_participant"),
    )
