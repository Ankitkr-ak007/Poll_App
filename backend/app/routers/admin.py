from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas, auth
from ..database import get_db

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

@router.get("/poll", response_model=schemas.PollResponse)
def get_poll(db: Session = Depends(get_db), current_admin: models.Admin = Depends(auth.get_current_admin)):
    poll = db.query(models.Poll).first()
    if not poll:
        # Auto-create draft poll if none exists
        poll = models.Poll(question="Default Question", option_a_text="Option A", option_b_text="Option B")
        db.add(poll)
        db.commit()
        db.refresh(poll)
    return poll

@router.put("/poll", response_model=schemas.PollResponse)
def update_poll(poll_update: schemas.PollUpdate, db: Session = Depends(get_db), current_admin: models.Admin = Depends(auth.get_current_admin)):
    poll = db.query(models.Poll).first()
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    if poll.status != "draft":
        raise HTTPException(status_code=400, detail="Cannot edit poll while not in draft status")
    
    poll.question = poll_update.question
    poll.option_a_text = poll_update.option_a_text
    poll.option_b_text = poll_update.option_b_text
    db.commit()
    db.refresh(poll)
    return poll

@router.post("/poll/open", response_model=schemas.PollResponse)
def open_poll(db: Session = Depends(get_db), current_admin: models.Admin = Depends(auth.get_current_admin)):
    poll = db.query(models.Poll).first()
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    if poll.status != "draft":
        raise HTTPException(status_code=400, detail="Poll is already active or closed")
    poll.status = "active"
    db.commit()
    db.refresh(poll)
    return poll

@router.post("/poll/close", response_model=schemas.PollResponse)
def close_poll(db: Session = Depends(get_db), current_admin: models.Admin = Depends(auth.get_current_admin)):
    poll = db.query(models.Poll).first()
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    if poll.status != "active":
        raise HTTPException(status_code=400, detail="Poll is not active")
    poll.status = "closed"
    poll.closed_at = models.func.now()
    db.commit()
    db.refresh(poll)
    return poll

@router.post("/poll/reset", response_model=schemas.PollResponse)
def reset_poll(confirm_data: schemas.ResetConfirm, db: Session = Depends(get_db), current_admin: models.Admin = Depends(auth.get_current_admin)):
    if not confirm_data.confirm:
        raise HTTPException(status_code=400, detail="Confirmation required")
    poll = db.query(models.Poll).first()
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    if poll.status != "closed":
        raise HTTPException(status_code=400, detail="Poll must be closed before resetting")
    
    poll.status = "draft"
    poll.closed_at = None
    
    # Reset participants' votes
    db.query(models.Participant).update({
        models.Participant.has_voted: False,
        models.Participant.voted_option: None,
        models.Participant.voted_at: None
    })
    
    db.commit()
    db.refresh(poll)
    return poll

@router.get("/results", response_model=schemas.PollResults)
def get_results(db: Session = Depends(get_db), current_admin: models.Admin = Depends(auth.get_current_admin)):
    poll = db.query(models.Poll).first()
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    
    participants = db.query(models.Participant).filter(models.Participant.poll_id == poll.id).all()
    
    option_a_count = sum(1 for p in participants if p.voted_option == 'A')
    option_b_count = sum(1 for p in participants if p.voted_option == 'B')
    total = sum(1 for p in participants if p.has_voted)
    
    participant_statuses = [schemas.ParticipantStatus(name=p.name, has_voted=p.has_voted) for p in participants]
    
    return schemas.PollResults(
        option_a=schemas.PollResultOption(text=poll.option_a_text, count=option_a_count),
        option_b=schemas.PollResultOption(text=poll.option_b_text, count=option_b_count),
        total=total,
        participants=participant_statuses
    )

@router.post("/participants", response_model=List[schemas.ParticipantResponse])
def add_participants(bulk_create: schemas.ParticipantBulkCreate, db: Session = Depends(get_db), current_admin: models.Admin = Depends(auth.get_current_admin)):
    poll = db.query(models.Poll).first()
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
    poll = db.query(models.Poll).first()
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
