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
from .. import tally_cache

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
    tally = tally_cache.increment_tally(str(poll.id), vote.option, db)
    
    await manager.broadcast_poll_results(str(poll.id), {
        "type": "vote",
        "option_a_count": tally["A"],
        "option_b_count": tally["B"],
        "total": tally["total"]
    })
    
    return {"status": "ok"}

@router.get("/results/{poll_id}", response_model=schemas.PublicPollResult)
def get_public_results(poll_id: str, db: Session = Depends(get_db)):
    poll = db.query(models.Poll).filter(models.Poll.id == poll_id).first()
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
        
    if poll.status == "closed":
        return schemas.PublicPollResult(
            question=poll.question,
            option_a_text=poll.option_a_text,
            option_b_text=poll.option_b_text,
            status=poll.status,
            counts=poll.final_counts or {"A": 0, "B": 0, "total": 0},
            winner_option=poll.winner_option
        )
    else:
        tally = tally_cache.get_tally(poll_id, db)
        return schemas.PublicPollResult(
            question=poll.question,
            option_a_text=poll.option_a_text,
            option_b_text=poll.option_b_text,
            status=poll.status,
            counts=tally,
            winner_option=None
        )

@router.get("/results/session/{session_id}", response_model=List[schemas.SessionLeaderboardEntry])
def get_session_leaderboard(session_id: str, db: Session = Depends(get_db)):
    polls = db.query(models.Poll).filter(
        models.Poll.session_id == session_id, 
        models.Poll.status == "closed"
    ).order_by(models.Poll.closed_at.desc()).all()
    
    return [
        schemas.SessionLeaderboardEntry(
            poll_id=p.id,
            question=p.question,
            winner_option=p.winner_option,
            counts=p.final_counts
        ) for p in polls
    ]
