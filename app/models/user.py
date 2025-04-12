from sqlalchemy import Boolean, Column, Integer, String, DateTime
from datetime import datetime
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.project import Project, UserProject, GlobalAccess

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String(255), nullable=True)
    reset_password_token = Column(String(255), nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owned_projects = relationship("Project", back_populates="owner", lazy="joined")
    project_accesses = relationship("UserProject", back_populates="user", lazy="joined")
    granted_accesses = relationship("GlobalAccess", back_populates="owner", foreign_keys="GlobalAccess.owner_id", lazy="joined")
    received_accesses = relationship("GlobalAccess", back_populates="user", foreign_keys="GlobalAccess.user_id", lazy="joined")
