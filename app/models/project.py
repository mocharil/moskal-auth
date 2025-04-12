from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base

class Language(str, enum.Enum):
    INDONESIA = "indonesia"
    ENGLISH = "english"

class GlobalRole(str, enum.Enum):
    STANDARD = "standard"
    OBSERVER = "observer"
    ADMINISTRATOR = "administrator"

class ProjectRole(str, enum.Enum):
    FULL_ACCESS = "full_access"
    PREVIEW_ONLY = "preview_only"

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    language = Column(Enum(Language), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="owned_projects", lazy="joined")
    user_projects = relationship("UserProject", back_populates="project", lazy="joined")

class UserProject(Base):
    __tablename__ = "user_projects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    role = Column(Enum(ProjectRole), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="project_accesses", lazy="joined")
    project = relationship("Project", back_populates="user_projects", lazy="joined")

class GlobalAccess(Base):
    __tablename__ = "global_accesses"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(Enum(GlobalRole), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id], back_populates="granted_accesses", lazy="joined")
    user = relationship("User", foreign_keys=[user_id], back_populates="received_accesses", lazy="joined")
