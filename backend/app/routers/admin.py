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
import json

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
        # Auto-create draft poll if none exists
        poll = models.Poll(question="Default Question", option_a_text="Option A", option_b_text="Option B")
        db.add(poll)
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

@router.post("/poll/reset", response_model=schemas.PollResponse)
async def reset_poll(confirm_data: schemas.ResetConfirm, db: Session = Depends(get_db), current_admin: models.Admin = Depends(auth.get_current_admin)):
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
    
    # Reset participants' votes
    db.query(models.Participant).update({
        models.Participant.has_voted: False,
        models.Participant.voted_option: None,
        models.Participant.voted_at: None
    })
    
    db.add(models.AdminAuditLog(admin_id=current_admin.id, action="reset_poll", poll_id=poll.id))
    db.commit()
    db.refresh(poll)
    
    await manager.broadcast_poll_results(str(poll.id), {"type": "status_update", "status": poll.status, "reset": True})
    return poll

@router.get("/results", response_model=schemas.PollResults)
def get_results(db: Session = Depends(get_db), current_admin: models.Admin = Depends(auth.get_current_admin)):
    poll = db.query(models.Poll).order_by(models.Poll.created_at.desc()).first()
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    
    participants = db.query(models.Participant).filter(models.Participant.poll_id == poll.id).all()
    
    tally = tally_cache.get_tally(str(poll.id), db)
    option_a_count = tally["A"]
    option_b_count = tally["B"]
    total = tally["total"]
    
    participant_statuses = [schemas.ParticipantStatus(name=p.name, has_voted=p.has_voted) for p in participants]
    
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
        
    participants = db.query(models.Participant).filter(models.Participant.poll_id == poll.id).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Has Voted", "Voted Option", "Voted At"])
    
    for p in participants:
        writer.writerow([
            p.name, 
            "Yes" if p.has_voted else "No", 
            p.voted_option if p.voted_option else "N/A", 
            p.voted_at.isoformat() if p.voted_at else "N/A"
        ])
        
    response = StreamingResponse(iter([output.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename=poll_results_{poll_id}.csv"
    return response

@router.post("/participants", response_model=List[schemas.ParticipantResponse])
def add_participants(bulk_create: schemas.ParticipantBulkCreate, db: Session = Depends(get_db), current_admin: models.Admin = Depends(auth.get_current_admin)):
    poll = db.query(models.Poll).order_by(models.Poll.created_at.desc()).first()
    if not poll:
        raise HTTPException(status_code=400, detail="Create a poll first")
    
    created_participants = []
    for name in bulk_create.names:
        name = name.strip()
        if not name:
            continue
        existing = db.query(models.Participant).filter(
            models.Participant.poll_id == poll.id,
            models.Participant.name == name
        ).first()
        if not existing:
            new_participant = models.Participant(poll_id=poll.id, name=name)
            db.add(new_participant)
            created_participants.append(new_participant)
    
    db.commit()
    for p in created_participants:
        db.refresh(p)
    return created_participants

@router.get("/participants", response_model=List[schemas.ParticipantResponse])
def get_participants(db: Session = Depends(get_db), current_admin: models.Admin = Depends(auth.get_current_admin)):
    poll = db.query(models.Poll).order_by(models.Poll.created_at.desc()).first()
    if not poll:
        return []
    return db.query(models.Participant).filter(models.Participant.poll_id == poll.id).all()

@router.delete("/participants/{participant_id}")
def delete_participant(participant_id: str, db: Session = Depends(get_db), current_admin: models.Admin = Depends(auth.get_current_admin)):
    participant = db.query(models.Participant).filter(models.Participant.id == participant_id).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    db.delete(participant)
    db.commit()
    return {"status": "ok"}
