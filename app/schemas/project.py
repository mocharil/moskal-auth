from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum

class Language(str, Enum):
    INDONESIA = "indonesia"
    ENGLISH = "english"

class GlobalRole(str, Enum):
    STANDARD = "standard"
    OBSERVER = "observer"
    ADMINISTRATOR = "administrator"

class ProjectRole(str, Enum):
    FULL_ACCESS = "full_access"
    PREVIEW_ONLY = "preview_only"

# Onboarding Schema
class OnboardingRequest(BaseModel):
    projects: List[str]
    language: Language
    keywords: Optional[List[str]] = None

# Project Schemas
class ProjectBase(BaseModel):
    name: str
    language: Language

class ProjectCreate(ProjectBase):
    pass

class ProjectKeyword(BaseModel):
    project_name: str
    relevan_keyword: List[str]
    owner_id: int
    project_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class Project(ProjectBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime
    keywords: Optional[List[str]] = None

    class Config:
        from_attributes = True  # New Pydantic v2 attribute for ORM mode

# Access Management Schemas
class GlobalAccessCreate(BaseModel):
    user_email: str
    role: GlobalRole

class GlobalAccessResponse(BaseModel):
    id: int
    user_id: int
    owner_id: int
    role: GlobalRole
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class GlobalAccess(GlobalAccessResponse):
    pass

class ProjectAccessCreate(BaseModel):
    user_email: str
    project_id: int
    role: ProjectRole

class ProjectAccess(BaseModel):
    user_id: int
    project_id: int
    role: ProjectRole
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # New Pydantic v2 attribute for ORM mode

# Project List Response Schemas
class ProjectAccessInfo(Project):
    role: ProjectRole
    access_type: str = "individual"  # individual or global

    class Config:
        from_attributes = True

class ProjectListResponse(BaseModel):
    owned_projects: List[Project]
    accessible_projects: List[ProjectAccessInfo]

    class Config:
        from_attributes = True

class ProjectDetailRequest(BaseModel):
    email: str
    project_name: str

class ProjectDetailResponse(BaseModel):
    name: str
    language: Language
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime
    keywords: Optional[List[str]] = None
    role: Optional[ProjectRole] = None
    access_type: Optional[str] = None  # 'owner', 'individual', 'global', or None
    owner_email: str
    owner_name: Optional[str] = None
    global_role: Optional[GlobalRole] = None

    class Config:
        from_attributes = True

class ProjectDelete(BaseModel):
    project_id: int

class AccessDelete(BaseModel):
    user_email: str
    project_id: Optional[int] = None  # None for global access deletion

class IndividualAccessListItem(BaseModel):
    user_id: int
    user_name: str
    user_email: str
    project_id: int
    project_name: str
    language: Language
    owner_id: int
    owner_name: str
    owner_email: str
    role: ProjectRole

    class Config:
        from_attributes = True

class IndividualAccessListResponse(BaseModel):
    items: List[IndividualAccessListItem]

    class Config:
        from_attributes = True

class GlobalAccessListItem(BaseModel):
    user_id: int
    user_name: str
    user_email: str
    owner_id: int
    owner_name: str
    owner_email: str
    role: GlobalRole

    class Config:
        from_attributes = True

class GlobalAccessListResponse(BaseModel):
    items: List[GlobalAccessListItem]

    class Config:
        from_attributes = True
