from datetime import datetime
from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    title: str
    script: str = Field(default="")


class Project(BaseModel):
    id: str
    title: str
    script: str
    status: str
    created_at: datetime
