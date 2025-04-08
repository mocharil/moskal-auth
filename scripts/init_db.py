from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import sys
import os

# Add the parent directory to Python path so we can import our app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.security import get_password_hash, generate_verification_token
from app.models.user import Base, User

def init_db():
    # Create database engine
    engine = create_engine(settings.DATABASE_URL)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create a session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Check if we already have users
        existing_user = db.query(User).first()
        if existing_user:
            print("Database already contains data. Skipping test data creation.")
            return

        # Create test users
        test_users = [
            {
                "name": "Admin User",
                "email": "admin@example.com",
                "password": "admin123",
                "is_active": True,
                "is_verified": True
            },
            {
                "name": "Regular User",
                "email": "user@example.com",
                "password": "user123",
                "is_active": True,
                "is_verified": False,
                "verification_token": generate_verification_token()
            },
            {
                "name": "Inactive User",
                "email": "inactive@example.com",
                "password": "inactive123",
                "is_active": False,
                "is_verified": False
            }
        ]
        
        # Add users to database
        for user_data in test_users:
            user = User(
                name=user_data["name"],
                email=user_data["email"],
                hashed_password=get_password_hash(user_data["password"]),
                is_active=user_data["is_active"],
                is_verified=user_data["is_verified"],
                verification_token=user_data.get("verification_token"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(user)
        
        # Commit the changes
        db.commit()
        print("Test data has been successfully added to the database.")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print("Database initialization completed.")
