# -*- coding: utf-8 -*-
"""
PostgreSQL Database Models и Configuration
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, Boolean, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/semantic_generator")

Base = declarative_base()

class Project(Base):
    """Модель проекта"""
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    topic = Column(String(255), nullable=False)
    intents = Column(ARRAY(String), nullable=False)  # PostgreSQL ARRAY
    locale = Column(String(10), default='ru')
    status = Column(String(50), default='draft')  # draft, completed, archived
    
    # Метаданные
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    versions = relationship("ProjectVersion", back_populates="project", cascade="all, delete-orphan")
    clusters = relationship("Cluster", back_populates="project", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Project {self.title}>"

class ProjectVersion(Base):
    """Модель версии проекта (история)"""
    __tablename__ = "project_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    clusters_data = Column(JSON, nullable=False)  # Полный снимок кластеров
    note = Column(Text, nullable=True)  # Описание версии
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relations
    project = relationship("Project", back_populates="versions")
    
    def __repr__(self):
        return f"<ProjectVersion {self.project_id} v{self.version_number}>"

class Cluster(Base):
    """Модель кластера"""
    __tablename__ = "clusters"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    cluster_id = Column(String(100), nullable=False)  # UUID из UpperGraph
    name = Column(String(500), nullable=False)
    gpt_intent = Column(String(50), nullable=True)
    demand_level = Column(String(20), nullable=True)
    parent_theme = Column(String(255), nullable=True)
    seed_examples = Column(ARRAY(String), nullable=True)
    tags = Column(ARRAY(String), nullable=True)
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relations
    project = relationship("Project", back_populates="clusters")
    
    def __repr__(self):
        return f"<Cluster {self.name}>"

class Export(Base):
    """Модель экспорта"""
    __tablename__ = "exports"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    format = Column(String(20), nullable=False)  # xlsx, csv, json
    file_path = Column(String(500), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Export {self.format}>"

# SQLAlchemy engine и session setup
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging

logger = logging.getLogger(__name__)

engine = None
SessionLocal = None
db_available = False

def init_db():
    """Инициализировать БД (создать таблицы) - опционально"""
    global engine, SessionLocal, db_available
    
    try:
        # Пытаемся подключиться к БД
        engine = create_engine(
            DATABASE_URL,
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            connect_args={"connect_timeout": 5}
        )
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Проверяем соединение
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        
        # Создаем таблицы
        Base.metadata.create_all(bind=engine)
        db_available = True
        logger.info("✅ PostgreSQL connected and tables initialized")
    except Exception as e:
        db_available = False
        logger.warning(f"⚠️ PostgreSQL not available: {str(e)}")
        logger.warning("⚠️ Projects API will not be available. Other features work fine.")
        engine = None
        SessionLocal = None

def get_db():
    """Dependency для получения DB session в FastAPI"""
    if not db_available or SessionLocal is None:
        logger.warning("Database not available")
        return None
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
