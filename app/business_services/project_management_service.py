from datetime import UTC, datetime
from uuid import uuid4

from app.application_core.metadata_storage import read_collection, write_collection
from app.request_schemas.project_schema import Project, ProjectCreate


class ProjectManagementService:
    def list_projects(self) -> list[Project]:
        return [Project(**row) for row in read_collection("projects")]

    def get_project(self, project_id: str) -> Project | None:
        for project in self.list_projects():
            if project.id == project_id:
                return project
        return None

    def create_project(self, payload: ProjectCreate) -> Project:
        project = Project(
            id=uuid4().hex,
            title=payload.title,
            script=payload.script,
            status="draft",
            created_at=datetime.now(UTC),
        )
        rows = read_collection("projects")
        rows.append(project.model_dump(mode="json"))
        write_collection("projects", rows)
        return project
