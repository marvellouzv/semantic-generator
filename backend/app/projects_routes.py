"""
Projects API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List
from .database import get_db
from .database import Project, ProjectVersion, Cluster
from .schemas import (
    ProjectCreate, ProjectUpdate, ProjectResponse, ProjectDetailResponse,
    ProjectVersionResponse, ProjectListResponse, SaveProjectRequest, ClusterData
)
from datetime import datetime

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])

@router.post("/", response_model=ProjectResponse)
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    """Создать новый проект"""
    try:
        db_project = Project(
            title=project.title,
            description=project.description,
            topic=project.topic,
            intents=project.intents,
            locale=project.locale
        )
        db.add(db_project)
        db.commit()
        db.refresh(db_project)
        return db_project
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error creating project: {str(e)}")

@router.get("/", response_model=ProjectListResponse)
def list_projects(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: str = Query(None)
):
    """Получить список проектов"""
    try:
        query = db.query(Project)
        
        if status:
            query = query.filter(Project.status == status)
        
        total = query.count()
        projects = query.order_by(desc(Project.created_at)).offset(skip).limit(limit).all()
        
        return {
            "projects": projects,
            "total": total,
            "page": skip // limit + 1,
            "per_page": limit
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{project_id}", response_model=ProjectDetailResponse)
def get_project(project_id: int, db: Session = Depends(get_db)):
    """Получить проект со всеми кластерами"""
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Получаем кластеры
        clusters = db.query(Cluster).filter(Cluster.project_id == project_id).all()
        
        project_data = ProjectDetailResponse.from_orm(project)
        project_data.clusters = [ClusterData.from_orm(c) for c in clusters]
        
        return project_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    db: Session = Depends(get_db)
):
    """Обновить проект"""
    try:
        db_project = db.query(Project).filter(Project.id == project_id).first()
        
        if not db_project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Обновляем только предоставленные поля
        if project_update.title:
            db_project.title = project_update.title
        if project_update.description is not None:
            db_project.description = project_update.description
        if project_update.status:
            db_project.status = project_update.status
        
        db_project.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(db_project)
        return db_project
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{project_id}/save-version")
def save_project_version(
    project_id: int,
    save_request: SaveProjectRequest,
    db: Session = Depends(get_db)
):
    """Сохранить версию проекта"""
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Удаляем старые кластеры
        db.query(Cluster).filter(Cluster.project_id == project_id).delete()
        
        # Добавляем новые кластеры
        for cluster_data in save_request.clusters:
            cluster = Cluster(
                project_id=project_id,
                cluster_id=cluster_data.cluster_id,
                name=cluster_data.name,
                gpt_intent=cluster_data.gpt_intent,
                demand_level=cluster_data.demand_level,
                parent_theme=cluster_data.parent_theme,
                seed_examples=cluster_data.seed_examples,
                tags=cluster_data.tags,
                notes=cluster_data.notes
            )
            db.add(cluster)
        
        # Создаем версию
        version_count = db.query(ProjectVersion).filter(
            ProjectVersion.project_id == project_id
        ).count()
        
        version = ProjectVersion(
            project_id=project_id,
            version_number=version_count + 1,
            clusters_data=[c.dict() for c in save_request.clusters],
            note=f"Version {version_count + 1}"
        )
        db.add(version)
        
        # Обновляем проект
        project.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(version)
        
        return ProjectVersionResponse.from_orm(version)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{project_id}/versions", response_model=List[ProjectVersionResponse])
def get_project_versions(project_id: int, db: Session = Depends(get_db)):
    """Получить историю версий проекта"""
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        versions = db.query(ProjectVersion).filter(
            ProjectVersion.project_id == project_id
        ).order_by(desc(ProjectVersion.created_at)).all()
        
        return [ProjectVersionResponse.from_orm(v) for v in versions]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{project_id}/restore/{version_number}")
def restore_version(
    project_id: int,
    version_number: int,
    db: Session = Depends(get_db)
):
    """Восстановить проект из предыдущей версии"""
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        version = db.query(ProjectVersion).filter(
            ProjectVersion.project_id == project_id,
            ProjectVersion.version_number == version_number
        ).first()
        
        if not version:
            raise HTTPException(status_code=404, detail="Version not found")
        
        # Удаляем текущие кластеры
        db.query(Cluster).filter(Cluster.project_id == project_id).delete()
        
        # Восстанавливаем кластеры из версии
        for cluster_data in version.clusters_data:
            cluster = Cluster(
                project_id=project_id,
                cluster_id=cluster_data.get("cluster_id"),
                name=cluster_data.get("name"),
                gpt_intent=cluster_data.get("gpt_intent"),
                demand_level=cluster_data.get("demand_level"),
                parent_theme=cluster_data.get("parent_theme"),
                seed_examples=cluster_data.get("seed_examples"),
                tags=cluster_data.get("tags"),
                notes=cluster_data.get("notes")
            )
            db.add(cluster)
        
        project.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {"success": True, "restored_from_version": version_number}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    """Удалить проект"""
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        db.delete(project)  # Каскадное удаление кластеров и версий
        db.commit()
        
        return {"success": True, "message": "Project deleted"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
