from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Dict
from datetime import datetime

Intent = Literal[
    "commercial",      # Коммерческие: купить, заказать
    "informational",   # Информационные: что такое, как работает  
    "service",         # Сервисные: ремонт, установка
    "price",           # Ценовые: стоимость, расценки
    "navigational",    # Навигационные: найти компанию
    "brand",           # Брендовые: конкретные марки
    "diy",             # Своими руками: инструкции
    "download",        # Скачать: файлы, документы
    "comparative",     # Сравнительные: лучший, рейтинг
    "problem",         # Проблемные: не работает, сломался
    "local",           # Локальные: рядом, в городе
    "urgent",          # Срочные: быстро, экстренно
    "reviews",         # Отзывы: мнения, опыт
    "legal",           # Правовые: лицензии, документы
    "technical"        # Технические: характеристики, спецификации
]

# Limits removed - no restrictions for maximum coverage

class UpperCluster(BaseModel):
    cluster_id: str
    name: str
    intent_mix: List[Intent]
    seed_examples: List[str] = []
    notes: str | None = None
    demand_level: str | None = None    # High/Medium/Low от GPT-5
    parent_category: str | None = None # Родительская категория (тип запроса из выбранных пользователем)
    parent_theme: str | None = None    # Parent Theme от GPT-5
    gpt_intent: str | None = None      # Исходный интент от GPT-5

class UpperGraph(BaseModel):
    topic: str
    locale: str = "ru-RU"
    intents_applied: List[Intent]
    clusters: List[UpperCluster]

class UpperGraphRequest(BaseModel):
    topic: str
    locale: str = "ru-RU"
    intents: List[Intent]
    brand_whitelist: Optional[List[str]] = None  # Список брендов для брендовых запросов
    template_id: Optional[str] = None  # ID шаблона для режима дополнения
    minus_words: Optional[List[str]] = None  # Минус-слова (запрещённые слова/фразы)
    regions: Optional[List[str]] = None      # Регионы для локальных запросов (можно несколько)


# Модели для системы шаблонов
class ClusterTemplate(BaseModel):
    id: str
    name: str
    description: str = ""
    topic: str
    locale: str = "ru-RU"
    intents_applied: List[Intent]
    clusters: List[UpperCluster]
    created_at: datetime
    updated_at: datetime
    cluster_count: int
    
class CreateTemplateRequest(BaseModel):
    name: str
    description: str = ""
    upper_graph: UpperGraph
    
class TemplateListResponse(BaseModel):
    templates: List[ClusterTemplate]
