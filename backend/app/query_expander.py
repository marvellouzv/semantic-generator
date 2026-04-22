"""
Модуль для расширения запросов на втором этапе с использованием gpt-5
Использует JSON schema для гарантированного получения структурированного ответа
"""
import asyncio
import json
import re
import os
from typing import List, Dict, Any
from .gpt5_wrapper import ask_gpt5

PRIMARY_MODEL = os.getenv("OPENAI_MODEL", os.getenv("OPENROUTER_MODEL", "openai/gpt-5.1"))

# PROMPT_STAGE2 (System) - краткий и четкий
PROMPT_STAGE2_SYSTEM = """Ты SEO strategist, расширяешь только новыми head-запросами (1–3 слова). 
Возвращай JSON по схеме, без пояснений. Работай на русском языке."""

# JSON Schema для ответа GPT-5
QUERY_EXPANSION_SCHEMA = {
    "type": "object",
    "properties": {
        "rows": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "head_query": {"type": "string"},
                    "intent": {
                        "type": "string",
                        "enum": ["commercial", "transactional", "informational", "navigational", "price", "local", "service"]
                    },
                    "demand": {"type": "string", "enum": ["High", "Medium", "Low"]},
                    "parent_theme": {"type": "string"}
                },
                "required": ["head_query", "intent", "demand", "parent_theme"],
                "additionalProperties": False
            },
            "minItems": 8,
            "maxItems": 20
        }
    },
    "required": ["rows"],
    "additionalProperties": False
}

async def generate_additional_queries(
    topic: str,
    locale: str = "ru-RU",
    additional_requirements: str = "",
    existing_queries: List[str] = None,
    parent_themes: List[str] = None,
    allowed_types: List[str] = None
) -> List[Dict[str, Any]]:
    """
    Генерирует дополнительные запросы на втором этапе используя JSON schema
    """
    if existing_queries is None:
        existing_queries = []
    if parent_themes is None:
        parent_themes = []
    if allowed_types is None:
        allowed_types = ["commercial", "informational", "service", "price", "local"]
    
    # Формируем данные для промпта
    allowed_types_csv = ", ".join(allowed_types)
    parent_themes_bulleted = "\n".join([f"- {theme}" for theme in parent_themes])
    
    # Группируем существующие запросы для исключения дубликатов
    existing_heads_block = ""
    if existing_queries:
        existing_heads_block = "\n".join([f"- {query}" for query in existing_queries[:20]])
    
    # Целевое количество новых запросов (15-20)
    target_count = min(20, max(15, len(existing_queries) // 2))
    
    # USER промпт
    user_prompt = f"""TOPIC: "{topic}"
ALLOWED TYPES: {allowed_types_csv}
USER NOTES: {additional_requirements}

PARENT THEMES:
{parent_themes_bulleted}

EXISTING HEADS (исключить):
{existing_heads_block}

TARGET COUNT: {target_count}

Сгенерируй {target_count} новых head-запросов (1-3 слова) на русском языке.
Распредели по Parent Themes. Избегай дубликатов с EXISTING HEADS."""

    try:
        print(f"[QueryExpander] Generating {target_count} additional queries for topic '{topic}'")
        print(f"[QueryExpander] Parent themes: {len(parent_themes)}")
        print(f"[QueryExpander] Existing queries: {len(existing_queries)}")
        
        print(f"[GPT5] Sending prompt to GPT-5 ({len(user_prompt)} chars)")
        print("----- PROMPT START -----")
        print(user_prompt)
        print("------ PROMPT END ------")
        
        response_text = await ask_gpt5(
            input_blocks=[
                {"role": "system", "content": [{"type": "input_text", "text": PROMPT_STAGE2_SYSTEM}]},
                {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
            ],
            model=PRIMARY_MODEL,
            max_output_tokens=1600,
        )
        
        if not response_text or not response_text.strip():
            raise Exception("Stage2: empty output_text (увеличь max_output_tokens или снизь target)")
        
        print(f"[QueryExpander] Response length: {len(response_text)} chars")
        print(f"[QueryExpander] Response preview: {response_text[:200]}...")
        
        # Парсим JSON
        try:
            data = json.loads(response_text)
            rows = data.get("rows", [])
            
            print(f"[QueryExpander] Parsed {len(rows)} rows from JSON")
            
            # Конвертируем в формат, ожидаемый фронтендом
            queries = []
            for row in rows:
                queries.append({
                    "query": row["head_query"],
                    "intent": row["intent"],
                    "demand_level": row["demand"],
                    "parent_theme": row["parent_theme"],
                    "tags": []  # Пока пустые теги
                })
            
            print(f"[QueryExpander] Generated {len(queries)} additional queries for topic '{topic}'")
            return queries
            
        except json.JSONDecodeError as e:
            print(f"[QueryExpander] JSON parsing error: {e}")
            print(f"[QueryExpander] Raw response: {response_text}")
            raise Exception(f"Stage2: invalid JSON response - {e}")
        
    except Exception as e:
        print(f"[QueryExpander] Error generating queries: {e}")
        # Fallback - возвращаем базовые запросы
        fallback_queries = [
            {"query": f"что такое {topic}", "intent": "informational", "demand_level": "High", "parent_theme": "Общая информация", "tags": []},
            {"query": f"как выбрать {topic}", "intent": "informational", "demand_level": "High", "parent_theme": "Выбор и покупка", "tags": []},
            {"query": f"где купить {topic}", "intent": "commercial", "demand_level": "High", "parent_theme": "Покупка", "tags": []},
            {"query": f"сколько стоит {topic}", "intent": "price", "demand_level": "High", "parent_theme": "Цены", "tags": []},
            {"query": f"лучший {topic}", "intent": "commercial", "demand_level": "Medium", "parent_theme": "Рекомендации", "tags": []}
        ]
        return fallback_queries
