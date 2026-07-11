from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas, auth
from ..database import get_db
from ..ws_manager import manager
from .. import tally_cache
import io
import csv
import io
import csv
import json
import secrets

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.post("/login", response_model=schemas.Token)
def login(admin_credentials: schemas.AdminLogin, db: Session = Depends(get_db)):
    admin = db.query(models.Admin).filter(models.Admin.username == admin_credentials.username).first()
    if not admin or not auth.verify_password(admin_credentials.password, admin.password_hash):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Credentials")
    
    access_token = auth.create_access_token(
        data={"sub": admin.username}, 
        expires_delta=auth.timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/session", response_model=schemas.SessionResponse)
def create_session(session_data: schemas.SessionCreate, db: Session = Depends(get_db), current_admin: models.Admin = Depends(auth.get_current_admin)):
    new_session = models.Session(name=session_data.name)
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session

@router.get("/session/{session_id}", response_model=schemas.SessionResponse)
def get_session(session_id: str, db: Session = Depends(get_db), current_admin: models.Admin = Depends(auth.get_current_admin)):
    session_obj = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")
    return session_obj

@router.patch("/session/{session_id}/ranking-publish", response_model=schemas.SessionResponse)
def toggle_ranking_publish(session_id: str, payload: schemas.RankingPublishRequest, db: Session = Depends(get_db), current_admin: models.Admin = Depends(auth.get_current_admin)):
    session_obj = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_obj.ranking_published = payload.published
    
    db.add(models.AdminAuditLog(admin_id=current_admin.id, action=f"ranking_publish_{payload.published}", poll_id=None))
    db.commit()
    db.refresh(session_obj)
    
    return session_obj

@router.post("/session/{session_id}/polls", response_model=schemas.PollResponse)
def add_poll_to_session(session_id: str, poll_data: schemas.PollCreate, db: Session = Depends(get_db), current_admin: models.Admin = Depends(auth.get_current_admin)):
    session_obj = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")
    
    existing_polls_count = db.query(models.Poll).filter(models.Poll.session_id == session_id).count()
    
    new_poll = models.Poll(
        session_id=session_obj.id,
        order_index=existing_polls_count,
        question=poll_data.question,
        option_a_text=poll_data.option_a_text,
        option_b_text=poll_data.option_b_text,
        status="draft"
    )
    db.add(new_poll)
    db.commit()
    db.refresh(new_poll)
    return new_poll

@router.get("/poll", response_model=schemas.PollResponse)
def get_poll(db: Session = Depends(get_db), current_admin: models.Admin = Depends(auth.get_current_admin)):
    poll = db.query(models.Poll).order_by(models.Poll.created_at.desc()).first()
    if not poll:
        new_session = models.Session(name="Default Session")
        db.add(new_session)
        db.flush()
        
        poll = models.Poll(
            session_id=new_session.id,
            question="Default Question", 
            option_a_text="Option A", 
            option_b_text="Option B"
        )
        db.add(poll)
        db.commit()
        db.refresh(poll)
    elif not poll.session_id:
        new_session = models.Session(name="Legacy Session")
        db.add(new_session)
        db.flush()
        poll.session_id = new_session.id
        db.query(models.Poll).filter(models.Poll.session_id == None).update({models.Poll.session_id: new_session.id})
        db.commit()
        db.refresh(poll)
        
    return poll

@router.put("/poll", response_model=schemas.PollResponse)
async def update_poll(poll_update: schemas.PollUpdate, db: Session = Depends(get_db), current_admin: models.Admin = Depends(auth.get_current_admin)):
    poll = db.query(models.Poll).order_by(models.Poll.created_at.desc()).first()
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    if poll.status != "draft":
        raise HTTPException(status_code=400, detail="Cannot edit poll while not in draft status")
    
    poll.question = poll_update.question
    poll.option_a_text = poll_update.option_a_text
    poll.option_b_text = poll_update.option_b_text
    db.commit()
    db.refresh(poll)
    
    # Audit log
    db.add(models.AdminAuditLog(admin_id=current_admin.id, action="edit_poll", poll_id=poll.id))
    db.commit()
    
    await manager.broadcast_poll_results(str(poll.id), {"type": "status_update", "status": poll.status, "poll": {"question": poll.question, "option_a_text": poll.option_a_text, "option_b_text": poll.option_b_text}})
    return poll

@router.post("/poll/open", response_model=schemas.PollResponse)
async def open_poll(db: Session = Depends(get_db), current_admin: models.Admin = Depends(auth.get_current_admin)):
    poll = db.query(models.Poll).order_by(models.Poll.created_at.desc()).first()
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    if poll.status != "draft":
        raise HTTPException(status_code=400, detail="Poll is already active or closed")
    poll.status = "active"
    
    db.add(models.AdminAuditLog(admin_id=current_admin.id, action="open_poll", poll_id=poll.id))
    db.commit()
    db.refresh(poll)
    
    await manager.broadcast_poll_results(str(poll.id), {"type": "status_update", "status": poll.status})
    return poll

@router.post("/poll/close", response_model=schemas.PollResponse)
async def close_poll(db: Session = Depends(get_db), current_admin: models.Admin = Depends(auth.get_current_admin)):
    poll = db.query(models.Poll).order_by(models.Poll.created_at.desc()).first()
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    if poll.status != "active":
        raise HTTPException(status_code=400, detail="Poll is not active")
    poll.status = "closed"
    poll.closed_at = models.func.now()
    
    # Save final counts and determine winner
    tally = tally_cache.get_tally(str(poll.id), db)
    poll.final_counts = tally
    if tally["A"] > tally["B"]:
        poll.winner_option = 'A'
    elif tally["B"] > tally["A"]:
        poll.winner_option = 'B'
    else:
        poll.winner_option = None # Tie
    
    db.add(models.AdminAuditLog(admin_id=current_admin.id, action="close_poll", poll_id=poll.id))
    db.commit()
    db.refresh(poll)
    
    await manager.broadcast_poll_results(str(poll.id), {"type": "status_update", "status": poll.status})
    return poll

@router.post("/poll/next-round", response_model=schemas.PollResponse)
async def next_round_poll(db: Session = Depends(get_db), current_admin: models.Admin = Depends(auth.get_current_admin)):
    poll = db.query(models.Poll).order_by(models.Poll.created_at.desc()).first()
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    if poll.status != "closed":
        raise HTTPException(status_code=400, detail="Current poll must be closed before starting next round")
    
    new_poll = models.Poll(
        session_id=poll.session_id,
        order_index=poll.order_index + 1,
        question=poll.question,
        option_a_text=poll.option_a_text,
        option_b_text=poll.option_b_text,
        status="draft"
    )
    db.add(new_poll)
    db.flush()
        
    db.add(models.AdminAuditLog(admin_id=current_admin.id, action="next_round_poll", poll_id=new_poll.id))
    db.commit()
    db.refresh(new_poll)
    
    await manager.broadcast_poll_results(str(poll.id), {"type": "status_update", "status": "draft", "reset": True})
    return new_poll

@router.post("/poll/reset-current", response_model=schemas.PollResponse)
async def reset_current_poll(confirm_data: schemas.ResetConfirm, db: Session = Depends(get_db), current_admin: models.Admin = Depends(auth.get_current_admin)):
    if not confirm_data.confirm:
        raise HTTPException(status_code=400, detail="Confirmation required")
    poll = db.query(models.Poll).order_by(models.Poll.created_at.desc()).first()
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    if poll.status != "closed":
        raise HTTPException(status_code=400, detail="Poll must be closed before resetting")
    
    poll.status = "draft"
    poll.closed_at = None
    poll.winner_option = None
    poll.final_counts = None
    
    tally_cache.clear_tally(str(poll.id))
    
    # Reset participants' votes completely
    db.query(models.RoundVote).filter(models.RoundVote.poll_id == poll.id).update({
        models.RoundVote.has_voted: False,
        models.RoundVote.voted_option: None,
        models.RoundVote.voted_at: None,
        models.RoundVote.device_token: None,
        models.RoundVote.last_vote_attempt_id: None
    })
    
    db.add(models.AdminAuditLog(admin_id=current_admin.id, action="reset_current_poll", poll_id=poll.id))
    db.commit()
    db.refresh(poll)
    
    await manager.broadcast_poll_results(str(poll.id), {"type": "status_update", "status": poll.status, "reset": True})
    return poll

@router.get("/results", response_model=schemas.PollResults)
def get_results(db: Session = Depends(get_db), current_admin: models.Admin = Depends(auth.get_current_admin)):
    poll = db.query(models.Poll).order_by(models.Poll.created_at.desc()).first()
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    
    rosters = db.query(models.Roster).filter(models.Roster.session_id == poll.session_id).all()
    round_votes = db.query(models.RoundVote).filter(models.RoundVote.poll_id == poll.id).all()
    voted_roster_ids = {rv.roster_id for rv in round_votes if rv.has_voted}
    
    tally = tally_cache.get_tally(str(poll.id), db)
    option_a_count = tally["A"]
    option_b_count = tally["B"]
    total = tally["total"]
    
    participant_statuses = [schemas.ParticipantStatus(name=r.name, has_voted=(r.id in voted_roster_ids), vote_code=r.vote_code) for r in rosters]
    
    return schemas.PollResults(
        option_a=schemas.PollResultOption(text=poll.option_a_text, count=option_a_count),
        option_b=schemas.PollResultOption(text=poll.option_b_text, count=option_b_count),
        total=total,
        participants=participant_statuses
    )

@router.get("/export/{poll_id}.csv")
def export_poll_csv(poll_id: str, db: Session = Depends(get_db), current_admin: models.Admin = Depends(auth.get_current_admin)):
    poll = db.query(models.Poll).filter(models.Poll.id == poll_id).first()
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
        
    results = db.query(models.Roster, models.RoundVote).outerjoin(
        models.RoundVote, 
        (models.RoundVote.roster_id == models.Roster.id) & (models.RoundVote.poll_id == poll.id)
    ).filter(models.Roster.session_id == poll.session_id).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Passcode", "Has Voted", "Voted Option", "Voted At"])
    
    for r, rv in results:
        has_voted = rv.has_voted if rv else False
        voted_opt = rv.voted_option if rv and rv.voted_option else "N/A"
        voted_at = rv.voted_at.isoformat() if rv and rv.voted_at else "N/A"
        writer.writerow([r.name, r.vote_code, "Yes" if has_voted else "No", voted_opt, voted_at])
        
    response = StreamingResponse(iter([output.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename=poll_results_{poll_id}.csv"
    return response

@router.post("/roster", response_model=List[schemas.RosterResponse])
def add_roster(bulk_create: schemas.RosterBulkCreate, db: Session = Depends(get_db), current_admin: models.Admin = Depends(auth.get_current_admin)):
    poll = db.query(models.Poll).order_by(models.Poll.created_at.desc()).first()
    if not poll or not poll.session_id:
        raise HTTPException(status_code=400, detail="Create a session first")
    
    created_rosters = []
    for line in bulk_create.names:
        line = line.strip()
        if not line:
            continue
            
        parts = [p.strip() for p in line.split(',')]
        name = parts[0]
        if not name:
            continue
            
        vote_code = parts[1] if len(parts) > 1 and parts[1] else secrets.token_urlsafe(6)
        
        existing = db.query(models.Roster).filter(
            models.Roster.session_id == poll.session_id,
            models.Roster.name == name
        ).first()
        
        if not existing:
            new_roster = models.Roster(
                session_id=poll.session_id, 
                name=name,
                vote_code=vote_code
            )
            db.add(new_roster)
            created_rosters.append(new_roster)
        else:
            # If the user explicitly provided a passcode for an existing name, update it
            if len(parts) > 1 and parts[1]:
                existing.vote_code = vote_code
                db.add(existing)
    
    db.commit()
    for r in created_rosters:
        db.refresh(r)
    return created_rosters

@router.get("/roster", response_model=List[schemas.RosterResponse])
def get_roster(db: Session = Depends(get_db), current_admin: models.Admin = Depends(auth.get_current_admin)):
    poll = db.query(models.Poll).order_by(models.Poll.created_at.desc()).first()
    if not poll or not poll.session_id:
        return []
    return db.query(models.Roster).filter(models.Roster.session_id == poll.session_id).order_by(models.Roster.name.asc()).all()

@router.delete("/roster/{roster_id}")
def delete_roster(roster_id: str, db: Session = Depends(get_db), current_admin: models.Admin = Depends(auth.get_current_admin)):
    roster = db.query(models.Roster).filter(models.Roster.id == roster_id).first()
    if not roster:
        raise HTTPException(status_code=404, detail="Roster not found")
    
    # Optional: cleanup round_votes if you want cascading, though sqlite cascades if configured
    db.query(models.RoundVote).filter(models.RoundVote.roster_id == roster.id).delete()
    
    db.delete(roster)
    db.commit()
    return {"status": "ok"}
