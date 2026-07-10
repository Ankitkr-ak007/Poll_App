from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas
from ..database import get_db
import time

# Simple in-memory rate limiter for /vote
IP_RATE_LIMIT = {}
RATE_LIMIT_WINDOW = 5 # seconds

from ..database import get_db
from ..ws_manager import manager

router = APIRouter(prefix="/api", tags=["public"])

@router.get("/poll", response_model=schemas.PollResponse)
def get_public_poll(db: Session = Depends(get_db)):
    poll = db.query(models.Poll).order_by(models.Poll.created_at.desc()).first()
    if not poll:
        raise HTTPException(status_code=404, detail="No poll found")
    return poll

@router.get("/participants/search", response_model=List[schemas.ParticipantPublic])
def search_participants(q: str = "", db: Session = Depends(get_db)):
    poll = db.query(models.Poll).order_by(models.Poll.created_at.desc()).first()
    if not poll:
        return []
    
    query = db.query(models.Participant).filter(models.Participant.poll_id == poll.id)
    if q:
        query = query.filter(models.Participant.name.ilike(f"%{q}%"))
    
    participants = query.limit(10).all()
    return participants

@router.post("/vote")
async def cast_vote(vote: schemas.VoteCreate, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    current_time = time.time()
    
    # Rate Limiting Logic
    if client_ip in IP_RATE_LIMIT:
        last_request_time = IP_RATE_LIMIT[client_ip]
        if current_time - last_request_time < RATE_LIMIT_WINDOW:
            raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")
    
    IP_RATE_LIMIT[client_ip] = current_time
    
    poll = db.query(models.Poll).order_by(models.Poll.created_at.desc()).first()
    if not poll or poll.status != "active":
        raise HTTPException(status_code=403, detail="Poll is not active")
    
    participant = db.query(models.Participant).filter(
        models.Participant.id == vote.participant_id,
        models.Participant.poll_id == poll.id
    ).first()
    
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    if participant.has_voted:
        raise HTTPException(status_code=409, detail="Already voted")
    
    if vote.option not in ['A', 'B']:
        raise HTTPException(status_code=400, detail="Invalid option")
    
    participant.has_voted = True
    participant.voted_option = vote.option
    participant.voted_at = models.func.now()
    
    # Add vote event for analytics
    db.add(models.VoteEvent(poll_id=poll.id, option=vote.option))
    
    db.commit()
    
    # Broadcast to WebSockets
    option_a_count = db.query(models.Participant).filter(models.Participant.poll_id == poll.id, models.Participant.voted_option == 'A').count()
    option_b_count = db.query(models.Participant).filter(models.Participant.poll_id == poll.id, models.Participant.voted_option == 'B').count()
    total = db.query(models.Participant).filter(models.Participant.poll_id == poll.id, models.Participant.has_voted == True).count()
    
    await manager.broadcast_poll_results(str(poll.id), {
        "type": "vote",
        "option_a_count": option_a_count,
        "option_b_count": option_b_count,
        "total": total
    })
    
    return {"status": "ok"}
