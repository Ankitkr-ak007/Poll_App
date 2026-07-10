import os
import sys
# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from sqlalchemy.orm import Session
from app.database import engine, SessionLocal
from app.models import Admin
from app.auth import get_password_hash
from app.config import settings

def create_admin():
    db: Session = SessionLocal()
    try:
        existing_admin = db.query(Admin).filter(Admin.username == settings.ADMIN_USERNAME).first()
        if existing_admin:
            print("Admin already exists")
            return
        
        hashed_password = get_password_hash(settings.ADMIN_PASSWORD)
        new_admin = Admin(
            username=settings.ADMIN_USERNAME,
            password_hash=hashed_password
        )
        db.add(new_admin)
        db.commit()
        print(f"Admin '{settings.ADMIN_USERNAME}' created successfully.")
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()
