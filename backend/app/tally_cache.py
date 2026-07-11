from typing import Dict, Any
from sqlalchemy.orm import Session
from . import models

# In-memory dictionary to store live tallies per poll_id
# Format: { "poll_id": { "A": count, "B": count, "total": total } }
live_tally: Dict[str, Dict[str, int]] = {}

def get_tally(poll_id: str, db: Session) -> Dict[str, int]:
    if str(poll_id) not in live_tally:
        # Hydrate from DB
        option_a = db.query(models.RoundVote).filter(
            models.RoundVote.poll_id == poll_id, 
            models.RoundVote.voted_option == 'A'
        ).count()
        option_b = db.query(models.RoundVote).filter(
            models.RoundVote.poll_id == poll_id, 
            models.RoundVote.voted_option == 'B'
        ).count()
        total = db.query(models.RoundVote).filter(
            models.RoundVote.poll_id == poll_id, 
            models.RoundVote.has_voted == True
        ).count()
        live_tally[str(poll_id)] = {
            "A": option_a,
            "B": option_b,
            "total": total
        }
    return live_tally[str(poll_id)]

def increment_tally(poll_id: str, option: str, db: Session) -> Dict[str, int]:
    tally = get_tally(poll_id, db)
    if option in ["A", "B"]:
        tally[option] += 1
        tally["total"] += 1
    return tally

def clear_tally(poll_id: str):
    if str(poll_id) in live_tally:
        del live_tally[str(poll_id)]
