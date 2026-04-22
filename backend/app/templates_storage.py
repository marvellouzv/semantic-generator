"""
Система сохранения и загрузки шаблонов кластеров.
Использует файловую систему для персистентного хранения.
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict

from .models import ClusterTemplate, UpperGraph, CreateTemplateRequest

# Абсолютные пути: фиксируем хранение в корневой папке репозитория
# backend/app/templates_storage.py - parents[2] = <repo_root>
REPO_ROOT = Path(__file__).resolve().parents[2]
PRIMARY_TEMPLATES_DIR = REPO_ROOT / "templates"
# Легаси-места, где могли сохраниться файлы при старте из другой CWD
LEGACY_TEMPLATE_DIRS = [
    Path(__file__).resolve().parents[1] / "templates",  # backend/templates
]
# Уникальный список директорий (на всякий случай)
_seen: set[str] = set()
TEMPLATE_DIRS: List[Path] = []
for d in [PRIMARY_TEMPLATES_DIR, *LEGACY_TEMPLATE_DIRS]:
    d = d.resolve()
    key = str(d)
    if key not in _seen:
        TEMPLATE_DIRS.append(d)
        _seen.add(key)

# Гарантируем наличие основной директории
PRIMARY_TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)


def migrate_legacy_templates() -> int:
    """Скопировать все шаблоны из легаси-директорий в основную директорию.
    Возвращает количество перенесённых файлов.
    """
    migrated_count = 0
    for base in LEGACY_TEMPLATE_DIRS:
        if not base.exists():
            continue
        for file_path in base.glob("*.json"):
            try:
                # проверяем, есть ли уже файл в primary
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                template_id = data.get("id") or str(uuid.uuid4())
                out_path = PRIMARY_TEMPLATES_DIR / f"{template_id}.json"
                if not out_path.exists():
                    # нормализуем id и name на всякий случай
                    data["id"] = template_id
                    if not data.get("name"):
                        data["name"] = "Импортированный шаблон"
                    with open(out_path, "w", encoding="utf-8") as out:
                        json.dump(data, out, ensure_ascii=False, indent=2)
                    migrated_count += 1
            except Exception:
                # пропускаем проблемные файлы
                continue
    return migrated_count


def _get_template_file_path(template_id: str) -> Path:
    """Получить путь к файлу шаблона в основной директории."""
    return PRIMARY_TEMPLATES_DIR / f"{template_id}.json"


def _iter_all_template_files() -> List[Path]:
    files: List[Path] = []
    for base in TEMPLATE_DIRS:
        if base.exists():
            files.extend(sorted(base.glob("*.json")))
    return files


def save_template(request: CreateTemplateRequest) -> ClusterTemplate:
    """Сохранить шаблон кластеров в основной директории (устойчиво к CWD)."""
    template_id = str(uuid.uuid4())
    now = datetime.now()
    
    template = ClusterTemplate(
        id=template_id,
        name=request.name,
        description=request.description,
        topic=request.upper_graph.topic,
        locale=request.upper_graph.locale,
        intents_applied=request.upper_graph.intents_applied,
        clusters=request.upper_graph.clusters,
        created_at=now,
        updated_at=now,
        cluster_count=len(request.upper_graph.clusters)
    )
    
    # Сохраняем только в PRIMARY_TEMPLATES_DIR
    file_path = _get_template_file_path(template_id)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(template.model_dump(mode='json'), f, ensure_ascii=False, indent=2)
    
    return template


def load_template(template_id: str) -> Optional[ClusterTemplate]:
    """Загрузить шаблон по ID, проверяя основную и легаси директории."""
    # Сначала пробуем основную директорию
    primary_path = _get_template_file_path(template_id)
    if primary_path.exists():
        try:
            with open(primary_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return ClusterTemplate(**data)
        except (json.JSONDecodeError, KeyError, TypeError):
            return None
    
    # Затем ищем в легаси директориях
    for base in TEMPLATE_DIRS:
        fp = base / f"{template_id}.json"
        if fp.exists():
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return ClusterTemplate(**data)
            except (json.JSONDecodeError, KeyError, TypeError):
                return None
    return None


def list_templates() -> List[ClusterTemplate]:
    """Получить список всех шаблонов из всех известных директорий.
    При совпадении ID побеждает наиболее новый по updated_at.
    """
    by_id: Dict[str, ClusterTemplate] = {}
    
    for file_path in _iter_all_template_files():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            tpl = ClusterTemplate(**data)
            existing = by_id.get(tpl.id)
            if not existing or (tpl.updated_at and existing.updated_at and tpl.updated_at > existing.updated_at):
                by_id[tpl.id] = tpl
        except (json.JSONDecodeError, KeyError, TypeError):
            # Пропускаем поврежденные файлы
            continue
    
    templates = list(by_id.values())
    # Сортируем по дате создания (новые первыми)
    templates.sort(key=lambda t: t.created_at, reverse=True)
    return templates


def delete_template(template_id: str) -> bool:
    """Удалить шаблон (из всех известных директорий)."""
    deleted = False
    for base in TEMPLATE_DIRS:
        file_path = base / f"{template_id}.json"
        if file_path.exists():
            try:
                file_path.unlink()
                deleted = True
            except OSError:
                # пробуем следующие
                continue
    return deleted


def template_to_upper_graph(template: ClusterTemplate) -> UpperGraph:
    """Преобразовать шаблон в UpperGraph для использования."""
    return UpperGraph(
        topic=template.topic,
        locale=template.locale,
        intents_applied=template.intents_applied,
        clusters=template.clusters
    )
