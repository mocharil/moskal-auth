from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
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
    ProjectAccess,
    ProjectListResponse,
    GlobalAccessResponse,
    ProjectAccessInfo,
    ProjectDetailRequest,
    ProjectDetailResponse,
    ProjectDelete,
    AccessDelete,
    GlobalAccessListResponse,
    GlobalAccessListItem,
    IndividualAccessListResponse,
    IndividualAccessListItem
)
from utils.relevan_keyword import get_relevan_keyword
from sqlalchemy import and_


router = APIRouter(
    prefix="/project",
    tags=["project"],
    dependencies=[Depends(get_current_user)]  # Add authentication for all project routes
)

@router.post("/detail", response_model=ProjectDetailResponse)
async def get_project_detail(
    request: ProjectDetailRequest,
    db: Session = Depends(get_db)
):
    # Get user by email
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get project by name and find access details
    project = db.query(Project).filter(
        and_(
            Project.name == request.project_name,
            Project.owner_id == user.id
        )
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get project owner details
    owner = db.query(User).filter(User.id == project.owner_id).first()
    
    # Get keywords
    keywords = db.execute(
        text("""
            SELECT relevan_keyword 
            FROM keyword_projects 
            WHERE project_id = :project_id 
            AND owner_id = :owner_id
        """),
        {"project_id": project.id, "owner_id": project.owner_id}
    ).fetchall()
    
    # Check access type and role
    access_type = "owner"
    role = None
    global_role = None
    
    if project.owner_id != user.id:
        # Check individual access
        individual_access = db.query(UserProject).filter(
            and_(
                UserProject.project_id == project.id,
                UserProject.user_id == user.id
            )
        ).first()
        
        if individual_access:
            access_type = "individual"
            role = individual_access.role
        else:
            # Check global access
            global_access = db.query(GlobalAccess).filter(
                and_(
                    GlobalAccess.owner_id == project.owner_id,
                    GlobalAccess.user_id == user.id
                )
            ).first()
            
            if global_access:
                access_type = "global"
                global_role = global_access.role
                role = ProjectRole.FULL_ACCESS if global_access.role == GlobalRole.ADMINISTRATOR else ProjectRole.PREVIEW_ONLY
            else:
                raise HTTPException(status_code=403, detail="No access to this project")

    return ProjectDetailResponse(
        name=project.name,
        language=project.language,
        id=project.id,
        owner_id=project.owner_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
        keywords=[k[0] for k in keywords] if keywords else None,
        role=role,
        access_type=access_type,
        owner_email=owner.email,
        owner_name=owner.full_name if hasattr(owner, 'full_name') else None,
        global_role=global_role
    )

@router.post(
    "/onboarding", 
    response_model=List[ProjectSchema],
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "example": {
                        "projects": ["Project A", "Project B", "Project C"],
                        "language": "indonesia",
                        "keywords": ["keyword1", "keyword2"] 
                    }
                }
            }
        }
    }
)
async def create_onboarding(
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Handle "All language" case by converting to "indonesia"
    if "language" in request and request["language"] == "All language":
        request["language"] = "indonesia"
    
    # Convert dict to OnboardingRequest for validation
    try:
        request = OnboardingRequest(**request)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
  
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

    # Create projects
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
    
    # Use provided keywords if available, otherwise generate them
    if request.keywords:
        # Save provided keywords to keyword_projects table
        for project in projects:
            for keyword in request.keywords:
                db.execute(
                    text("""
                        INSERT INTO keyword_projects (project_id, owner_id, relevan_keyword, project_name, created_at)
                        VALUES (:project_id, :owner_id, :keyword, :project_name, :created_at)
                    """),
                    {
                        "project_id": project.id,
                        "owner_id": current_user.id,
                        "keyword": keyword,
                        "project_name": project.name,
                        "created_at": project.created_at
                    }
                )
            project.keywords = request.keywords
        db.commit()
    else:
        # Generate keywords using get_relevan_keyword
        keywords_response = get_relevan_keyword(projects)
        
        if keywords_response["status"] == "success":
            # Group keywords by project_id
            keywords_by_project = {}
            for item in keywords_response["data"]:
                project_id = item["project_id"]
                if project_id not in keywords_by_project:
                    keywords_by_project[project_id] = []
                keywords_by_project[project_id].append(item["relevan_keyword"])
            
            # Update each project with its keywords
            for project in projects:
                if project.id in keywords_by_project:
                    project.keywords = list(set(keywords_by_project[project.id]))

    return projects

@router.post("/access/global", response_model=GlobalAccessResponse)
async def create_global_access(
    access: GlobalAccessCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if user exists
    user = db.query(User).filter(User.email == access.user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if access already exists
    existing_access = db.query(GlobalAccess).filter(
        GlobalAccess.owner_id == current_user.id,
        GlobalAccess.user_id == user.id
    ).first()
    
    if existing_access:
        raise HTTPException(status_code=400, detail="Access already exists")
    
    global_access = GlobalAccess(
        owner_id=current_user.id,
        user_id=user.id,
        role=access.role
    )
    db.add(global_access)
    db.commit()
    db.refresh(global_access)
    
    return global_access

@router.post("/access/project", response_model=ProjectAccess)
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
    user = db.query(User).filter(User.email == access.user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if access already exists
    existing_access = db.query(UserProject).filter(
        UserProject.project_id == access.project_id,
        UserProject.user_id == user.id
    ).first()
    
    if existing_access:
        raise HTTPException(status_code=400, detail="Access already exists")
    
    project_access = UserProject(
        project_id=access.project_id,
        user_id=user.id,
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
    # Get owned projects with keywords
    owned_projects_query = db.query(Project).filter(
        Project.owner_id == current_user.id
    )
    
    owned_projects = []
    for project in owned_projects_query.all():
        # Get keywords for each project
        keywords = db.execute(
            text("""
                SELECT relevan_keyword 
                FROM keyword_projects 
                WHERE project_id = :project_id 
                AND owner_id = :owner_id
            """),
            {"project_id": project.id, "owner_id": current_user.id}
        ).fetchall()
        
        # Convert keywords to list
        project_keywords = [k[0] for k in keywords] if keywords else None
        
        # Create a dict with project attributes
        project_dict = {
            "id": project.id,
            "name": project.name,
            "owner_id": project.owner_id,
            "language": project.language,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
            "keywords": project_keywords
        }
        owned_projects.append(project_dict)
    
    # Get projects with individual access
    individual_accesses = db.query(UserProject).filter(
        UserProject.user_id == current_user.id
    ).all()
    
    # Get projects through global access
    global_accesses = db.query(GlobalAccess).filter(
        GlobalAccess.user_id == current_user.id
    ).all()
    
    accessible_projects = []
    added_project_ids = set()  # Track which projects have been added
    
    # Add individually accessible projects first
    for access in individual_accesses:
        project = access.project
        if project.id not in added_project_ids:  # Only add if not already added
            # Get keywords for the project
            keywords = db.execute(
                text("""
                    SELECT relevan_keyword 
                    FROM keyword_projects 
                    WHERE project_id = :project_id 
                    AND owner_id = :owner_id
                """),
                {"project_id": project.id, "owner_id": project.owner_id}
            ).fetchall()
            
            # Convert keywords to list and set it on the project
            project.keywords = [k[0] for k in keywords] if keywords else None
            
            accessible_projects.append(
                ProjectAccessInfo(
                    name=project.name,
                    language=project.language,
                    id=project.id,
                    owner_id=project.owner_id,
                    created_at=project.created_at,
                    updated_at=project.updated_at,
                    keywords=project.keywords,
                    role=access.role,
                    access_type="individual"
                )
            )
            added_project_ids.add(project.id)
    

    # Add globally accessible projects
    for global_access in global_accesses:
        owner_projects = db.query(Project).filter(
            Project.owner_id == global_access.owner_id
        ).all()
        
        for project in owner_projects:
            # Skip if project already added through individual access
            if project.id not in added_project_ids:
                # Get keywords for the project
                keywords = db.execute(
                    text("""
                        SELECT relevan_keyword 
                        FROM keyword_projects 
                        WHERE project_id = :project_id 
                        AND owner_id = :owner_id
                    """),
                    {"project_id": project.id, "owner_id": project.owner_id}
                ).fetchall()
                
                # Convert keywords to list and set it on the project
                project.keywords = [k[0] for k in keywords] if keywords else None
                
                # Map global role to project role
                project_role = ProjectRole.FULL_ACCESS if global_access.role == GlobalRole.ADMINISTRATOR else ProjectRole.PREVIEW_ONLY
                
                accessible_projects.append(
                    ProjectAccessInfo(
                        name=project.name,
                        language=project.language,
                        id=project.id,
                        owner_id=project.owner_id,
                        created_at=project.created_at,
                        updated_at=project.updated_at,
                        keywords=project.keywords,
                        role=project_role,
                        access_type="global"
                    )
                )
                added_project_ids.add(project.id)
    
    list_owned_project_ids = [p["id"] for p in owned_projects]
    return ProjectListResponse(
        owned_projects=owned_projects,
        accessible_projects=[i for i in accessible_projects if i.id not in list_owned_project_ids]
    )

@router.delete("/remove")
async def remove_project(
    request: ProjectDelete,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if project exists and user is owner
    
    project = db.query(Project).filter(
        and_(
            Project.id == request.project_id,
            Project.owner_id == current_user.id
        )
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or you're not the owner")
    
    # Delete associated keywords
    db.execute(
        text("""
            DELETE FROM keyword_projects 
            WHERE project_id = :project_id 
            AND owner_id = :owner_id
        """),
        {"project_id": project.id, "owner_id": current_user.id}
    )
    
    # Delete associated access records
    db.query(UserProject).filter(UserProject.project_id == project.id).delete()
    
    # Delete the project
    db.delete(project)
    db.commit()
    
    return {"message": "Project successfully deleted"}

@router.delete("/access/remove")
async def remove_access(
    request: AccessDelete,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get user by email
    user = db.query(User).filter(User.email == request.user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if request.project_id:
        # Remove individual project access
        project = db.query(Project).filter(
            and_(
                Project.id == request.project_id,
                Project.owner_id == current_user.id
            )
        ).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found or you're not the owner")
        
        access = db.query(UserProject).filter(
            and_(
                UserProject.project_id == request.project_id,
                UserProject.user_id == user.id
            )
        ).first()
        
        if not access:
            raise HTTPException(status_code=404, detail="Access not found")
        
        db.delete(access)
        db.commit()
        
        return {"message": "Project access successfully removed"}
    else:
        # Remove global access
        access = db.query(GlobalAccess).filter(
            and_(
                GlobalAccess.owner_id == current_user.id,
                GlobalAccess.user_id == user.id
            )
        ).first()
        
        if not access:
            raise HTTPException(status_code=404, detail="Global access not found")
        
        db.delete(access)
        db.commit()
        
        return {"message": "Global access successfully removed"}

@router.get("/access/global-access/list", response_model=GlobalAccessListResponse)
async def list_global_access(
    owner_email: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Execute the query
    result = db.execute(
        text("""
            select ga.*, owner_name, owner_email, user_name, user_email from global_accesses ga
            join (select id, name owner_name, email owner_email from users) owner 
            on ga.owner_id = owner.id
            join (select id, name user_name, email user_email from users) user 
            on ga.user_id = user.id
            where owner_email = :owner_email
        """),
        {"owner_email": owner_email}
    ).fetchall()

    # Transform the results into the response format
    items = [
        GlobalAccessListItem(
            user_id = row.user_id,
            user_name=row.user_name,
            user_email=row.user_email,
            owner_id=row.owner_id,
            owner_name=row.owner_name,
            owner_email=row.owner_email,
            role=row.role.lower()  # Convert to lowercase to match enum
        )
        for row in result
    ]

    return GlobalAccessListResponse(items=items)

@router.get("/access/individual-project-access/list", response_model=IndividualAccessListResponse)
async def list_individual_project_access(
    owner_email: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Execute the query
    result = db.execute(
        text("""
            select ga.user_id, ga.project_id, lower(ga.role) role, ga.created_at, ga.updated_at, user_name, user_email, project_name, p.language, 
            p.owner_id, p.owner_name, p.owner_email

            from user_projects ga
            join (select id, name user_name, email user_email from users) user 
            on ga.user_id = user.id
            join (select projects.id, projects.name project_name, language, owner_id , users.name owner_name, users.email owner_email from projects
                    join users 
                    on users.id = projects.owner_id
            ) p 
            on p.id = ga.project_id
            where p.owner_email = :owner_email
        """),
        {"owner_email": owner_email}
    ).fetchall()

    # Transform the results into the response format
    items = [
        IndividualAccessListItem(
            user_id=row.user_id,
            project_id=row.project_id,
            user_name=row.user_name,
            user_email=row.user_email,
            project_name=row.project_name,
            language=row.language.lower(),  # Convert to lowercase to match enum
            owner_id=row.owner_id,
            owner_name=row.owner_name,
            owner_email=row.owner_email,
            role=row.role  # This should be FULL_ACCESS or PREVIEW_ONLY
        )
        for row in result
    ]

    return IndividualAccessListResponse(items=items)
