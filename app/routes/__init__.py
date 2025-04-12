from fastapi import APIRouter
from app.routes.auth import router as auth_router
from app.routes.project import router as project_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])
api_router.include_router(project_router, tags=["project"])  # Remove prefix since it's already set in project_router
