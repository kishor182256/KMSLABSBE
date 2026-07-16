from fastapi import APIRouter, HTTPException

from app.business_services.project_management_service import ProjectManagementService
from app.request_schemas.project_schema import Project, ProjectCreate

router = APIRouter(prefix="/projects", tags=["projects"])
service = ProjectManagementService()


@router.post("", response_model=Project, status_code=201)
def create_project(payload: ProjectCreate) -> Project:
    return service.create_project(payload)


@router.get("", response_model=list[Project])
def list_projects() -> list[Project]:
    return service.list_projects()


@router.get("/{project_id}", response_model=Project)
def get_project(project_id: str) -> Project:
    project = service.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
