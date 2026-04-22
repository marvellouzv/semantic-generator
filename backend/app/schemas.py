"""
Pydantic schemas для API endpoints
"""
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# Project Schemas
class ProjectCreate(BaseModel):
    title: str
    description: Optional[str] = None
    topic: str
    intents: List[str]
    locale: str = "ru"

class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None

class ClusterData(BaseModel):
    cluster_id: str
    name: str
    gpt_intent: Optional[str] = None
    demand_level: Optional[str] = None
    parent_theme: Optional[str] = None
    seed_examples: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None

class ProjectResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    topic: str
    intents: List[str]
    locale: str
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ProjectDetailResponse(ProjectResponse):
    clusters: List[ClusterData] = []

class ProjectVersionResponse(BaseModel):
    id: int
    project_id: int
    version_number: int
    note: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class ProjectListResponse(BaseModel):
    projects: List[ProjectResponse]
    total: int
    page: int
    per_page: int

class SaveProjectRequest(BaseModel):
    title: str
    description: Optional[str] = None
    clusters: List[ClusterData]
