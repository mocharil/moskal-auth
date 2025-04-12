from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.project import Project, UserProject, GlobalAccess, ProjectRole, GlobalRole
from app.schemas.project import (
    OnboardingRequest,
    ProjectCreate,
    Project as ProjectSchema,
    GlobalAccessCreate,
    ProjectAccessCreate,
    ProjectListResponse,
    ProjectAccessInfo
)

router = APIRouter(
    prefix="/project",
    tags=["project"],
    dependencies=[Depends(get_current_user)]  # Add authentication for all project routes
)

@router.post("/onboarding", response_model=List[ProjectSchema])
async def create_onboarding(
    request: OnboardingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check for duplicate project names
    for project_name in request.projects:
        existing_project = db.query(Project).filter(
            Project.owner_id == current_user.id,
            Project.name == project_name
        ).first()
        if existing_project:
            raise HTTPException(
                status_code=400,
                detail=f"Project with name '{project_name}' already exists for this user"
            )

    projects = []
    for project_name in request.projects:
        project = Project(
            name=project_name,
            owner_id=current_user.id,
            language=request.language
        )
        db.add(project)
        projects.append(project)
    
    db.commit()
    for project in projects:
        db.refresh(project)
    
    return projects

@router.post("/access/global", response_model=GlobalAccessCreate)
async def create_global_access(
    access: GlobalAccessCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if user exists
    user = db.query(User).filter(User.id == access.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if access already exists
    existing_access = db.query(GlobalAccess).filter(
        GlobalAccess.owner_id == current_user.id,
        GlobalAccess.user_id == access.user_id
    ).first()
    
    if existing_access:
        raise HTTPException(status_code=400, detail="Access already exists")
    
    global_access = GlobalAccess(
        owner_id=current_user.id,
        user_id=access.user_id,
        role=access.role
    )
    db.add(global_access)
    db.commit()
    db.refresh(global_access)
    
    return global_access

@router.post("/access/project", response_model=ProjectAccessCreate)
async def create_project_access(
    access: ProjectAccessCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if project exists and user is owner
    project = db.query(Project).filter(
        Project.id == access.project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or you're not the owner")
    
    # Check if user exists
    user = db.query(User).filter(User.id == access.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if access already exists
    existing_access = db.query(UserProject).filter(
        UserProject.project_id == access.project_id,
        UserProject.user_id == access.user_id
    ).first()
    
    if existing_access:
        raise HTTPException(status_code=400, detail="Access already exists")
    
    project_access = UserProject(
        project_id=access.project_id,
        user_id=access.user_id,
        role=access.role
    )
    db.add(project_access)
    db.commit()
    db.refresh(project_access)
    
    return project_access

@router.get("/projects", response_model=ProjectListResponse)
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get owned projects
    owned_projects = db.query(Project).filter(
        Project.owner_id == current_user.id
    ).all()
    
    # Get projects with individual access
    individual_accesses = db.query(UserProject).filter(
        UserProject.user_id == current_user.id
    ).all()
    
    # Get projects through global access
    global_accesses = db.query(GlobalAccess).filter(
        GlobalAccess.user_id == current_user.id
    ).all()
    
    accessible_projects = []
    
    # Add individually accessible projects
    for access in individual_accesses:
        accessible_projects.append(
            ProjectAccessInfo(
                project=access.project,
                role=access.role,
                access_type="individual"
            )
        )
    
    # Add globally accessible projects
    for global_access in global_accesses:
        owner_projects = db.query(Project).filter(
            Project.owner_id == global_access.owner_id
        ).all()
        
        for project in owner_projects:
            # Map global role to project role
            project_role = ProjectRole.FULL_ACCESS if global_access.role == GlobalRole.ADMINISTRATOR else ProjectRole.PREVIEW_ONLY
            
            accessible_projects.append(
                ProjectAccessInfo(
                    project=project,
                    role=project_role,
                    access_type="global"
                )
            )
    
    return ProjectListResponse(
        owned_projects=owned_projects,
        accessible_projects=accessible_projects
    )
