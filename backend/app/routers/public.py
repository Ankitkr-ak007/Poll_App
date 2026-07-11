from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas
from ..database import get_db
import time
import uuid

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

@router.get("/vote/status", response_model=schemas.VoteStatusResponse)
def check_vote_status(poll_id: str, request: Request, response: Response, db: Session = Depends(get_db)):
    device_token = request.cookies.get("device_token")
    if not device_token:
        device_token = str(uuid.uuid4())
        response.set_cookie(key="device_token", value=device_token, httponly=True, secure=True, samesite="none")
        return {"already_voted": False}
    
    participant = db.query(models.Participant).filter(
        models.Participant.poll_id == poll_id,
        models.Participant.device_token == device_token,
        models.Participant.has_voted == True
    ).first()
    
    if participant:
        return {"already_voted": True, "name": participant.name, "option": participant.voted_option}
    
    return {"already_voted": False}

@router.post("/vote")
async def cast_vote(vote: schemas.VoteCreate, request: Request, response: Response, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    current_time = time.time()
    
    # Rate Limiting Logic
    if client_ip in IP_RATE_LIMIT:
        last_request_time = IP_RATE_LIMIT[client_ip]
        if current_time - last_request_time < RATE_LIMIT_WINDOW:
            raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")
    
    IP_RATE_LIMIT[client_ip] = current_time

    device_token = request.cookies.get("device_token")
    if not device_token:
        device_token = str(uuid.uuid4())
        response.set_cookie(key="device_token", value=device_token, httponly=True, secure=True, samesite="none")
    
    poll = db.query(models.Poll).order_by(models.Poll.created_at.desc()).first()
    if not poll or poll.status != "active":
        raise HTTPException(status_code=403, detail="Poll is not active")
    
    participant = db.query(models.Participant).filter(
        models.Participant.id == vote.participant_id,
        models.Participant.poll_id == poll.id
    ).first()
    
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    # Check if this device already voted as someone else
    existing_device_vote = db.query(models.Participant).filter(
        models.Participant.poll_id == poll.id,
        models.Participant.device_token == device_token,
        models.Participant.has_voted == True
    ).first()

    if existing_device_vote and str(existing_device_vote.id) != str(participant.id):
        raise HTTPException(status_code=409, detail=f"This device already voted as {existing_device_vote.name} in this round.")
    
    if participant.has_voted:
        if participant.last_vote_attempt_id == vote.vote_attempt_id:
            return {"status": "ok", "idempotent": True}
        raise HTTPException(status_code=409, detail="Already voted")
    
    if vote.option not in ['A', 'B']:
        raise HTTPException(status_code=400, detail="Invalid option")
    
    participant.has_voted = True
    participant.voted_option = vote.option
    participant.voted_at = models.func.now()
    participant.last_vote_attempt_id = vote.vote_attempt_id
    participant.device_token = device_token
    
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

@router.get("/results/session/{session_id}", response_model=schemas.PublicSessionRankingResponse)
def get_session_leaderboard(session_id: str, db: Session = Depends(get_db)):
    session_obj = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")
        
    if not session_obj.ranking_published:
        return schemas.PublicSessionRankingResponse(published=False, rounds=None)
        
    polls = db.query(models.Poll).filter(
        models.Poll.session_id == session_id, 
        models.Poll.status == "closed"
    ).order_by(models.Poll.closed_at.desc()).all()
    
    rounds = []
    for p in polls:
        counts = p.final_counts or {"A": 0, "B": 0, "total": 0}
        total = counts.get("total", 0)
        
        roster_size = db.query(models.Participant).filter(models.Participant.poll_id == p.id).count()
        voted_count = db.query(models.Participant).filter(models.Participant.poll_id == p.id, models.Participant.has_voted == True).count()
        
        percentages = {
            "A": round((counts.get("A", 0) / total * 100), 1) if total > 0 else 0,
            "B": round((counts.get("B", 0) / total * 100), 1) if total > 0 else 0
        }
        
        result_label = None
        if counts.get("A", 0) > counts.get("B", 0):
            result_label = "A"
        elif counts.get("B", 0) > counts.get("A", 0):
            result_label = "B"
            
        rounds.append(schemas.RoundRanking(
            poll_id=p.id,
            question=p.question,
            option_a_text=p.option_a_text,
            option_b_text=p.option_b_text,
            counts=counts,
            percentages=percentages,
            participation={"voted": voted_count, "total": roster_size},
            result_label=result_label
        ))
    
    return schemas.PublicSessionRankingResponse(published=True, rounds=rounds)
