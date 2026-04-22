"""
GPT очистка и улучшение запросов после детерминированной генерации.
"""

import json
import asyncio
from typing import List, Dict, Any
from .models import Intent

# Промпт для очистки запросов
CLEANUP_PROMPT = """Ты — SEO-редактор. Быстро переформулируй запросы в естественные.

ЗАДАЧА: Исправь запросы для русского поиска.

БЫСТРЫЕ ПРАВИЛА:
- Убери дубли слов: "ремонт ремонт окон" -> "ремонт окон"
- Исправь порядок: "услуги как типы" -> "типы услуг"
- Сохрани смысл
- 2-7 слов

ОТВЕТ: JSON массив строк той же длины."""

async def cleanup_queries_batch(queries: List[str], openai_function) -> List[str]:
    """Очищает пакет запросов через GPT."""
    
    if not queries:
        return []
    
    # Подготавливаем данные для GPT
    user_data = {
        "queries": queries,
        "count": len(queries)
    }
    
    try:
        # Простая схема для массива строк
        cleanup_schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "cleaned_queries": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": len(queries),
                    "maxItems": len(queries)
                }
            },
            "required": ["cleaned_queries"]
        }
        
        result = await openai_function(cleanup_schema, CLEANUP_PROMPT, user_data, "gpt-5")
        
        cleaned = result.get("cleaned_queries", [])
        
        # Проверяем результат
        if len(cleaned) != len(queries):
            print(f"Warning: GPT returned {len(cleaned)} queries, expected {len(queries)}")
            # Дополняем или обрезаем до нужного размера
            if len(cleaned) < len(queries):
                cleaned.extend(queries[len(cleaned):])  # Добавляем оригинальные
            else:
                cleaned = cleaned[:len(queries)]  # Обрезаем
        
        return cleaned
        
    except Exception as e:
        print(f"GPT cleanup failed: {e}, returning original queries")
        return queries

async def cleanup_cluster_queries(cluster: Dict[str, Any], openai_function, batch_size: int = 100) -> Dict[str, Any]:
    """Очищает запросы одного кластера."""
    cluster_name = cluster.get("cluster_name", "")
    queries = cluster.get("queries", [])
    
    if not queries:
        return cluster
    
    # Извлекаем только текст запросов для очистки
    query_texts = [q.get("q", "") for q in queries]
    
    # Очищаем пакетами
    cleaned_texts = []
    for i in range(0, len(query_texts), batch_size):
        batch = query_texts[i:i + batch_size]
        cleaned_batch = await cleanup_queries_batch(batch, openai_function)
        cleaned_texts.extend(cleaned_batch)
    
    # Создаем новые объекты запросов с очищенным текстом
    cleaned_queries = []
    for i, original_query in enumerate(queries):
        if i < len(cleaned_texts):
            cleaned_query = {
                **original_query,
                "q": cleaned_texts[i]
            }
            cleaned_queries.append(cleaned_query)
    
    return {
        **cluster,
        "queries": cleaned_queries
    }

async def cleanup_all_queries(expanded_data: Dict[str, Any], openai_function, batch_size: int = 100) -> Dict[str, Any]:
    """Очищает все запросы параллельно через GPT."""
    
    clusters = expanded_data.get("expanded", [])
    total_queries = sum(len(cluster.get("queries", [])) for cluster in clusters)
    
    print(f"Starting parallel GPT cleanup of {total_queries} queries across {len(clusters)} clusters...")
    
    # Параллельная обработка кластеров (по 5 одновременно для экономии API лимитов)
    cleaned_expanded = []
    parallel_limit = 3  # Обрабатываем по 3 кластера одновременно
    
    for i in range(0, len(clusters), parallel_limit):
        batch_clusters = clusters[i:i + parallel_limit]
        
        print(f"Processing clusters {i+1}-{min(i+parallel_limit, len(clusters))} of {len(clusters)}")
        
        # Параллельная обработка пакета кластеров
        tasks = [
            cleanup_cluster_queries(cluster, openai_function, batch_size)
            for cluster in batch_clusters
        ]
        
        cleaned_batch = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Обрабатываем результаты
        for j, result in enumerate(cleaned_batch):
            if isinstance(result, Exception):
                print(f"Cluster {i+j+1} cleanup failed: {result}, using original")
                cleaned_expanded.append(batch_clusters[j])
            else:
                cleaned_expanded.append(result)
    
    result = {
        **expanded_data,
        "expanded": cleaned_expanded
    }
    
    total_cleaned = sum(len(cluster.get("queries", [])) for cluster in cleaned_expanded)
    print(f"Parallel GPT cleanup completed: {total_cleaned} queries cleaned")
    
    return result

def improve_deterministic_quality(queries: List[str], base_topic: str) -> List[str]:
    """Улучшает качество детерминированно сгенерированных запросов."""
    
    improved = []
    
    for query in queries:
        # Убираем дублированные слова
        words = query.split()
        unique_words = []
        seen = set()
        
        for word in words:
            if word.lower() not in seen:
                unique_words.append(word)
                seen.add(word.lower())
        
        # Исправляем порядок слов
        improved_query = " ".join(unique_words)
        
        # Базовые исправления
        improved_query = improved_query.replace("ремонт ремонт", "ремонт")
        improved_query = improved_query.replace("окон окон", "окон")
        improved_query = improved_query.replace("услуги услуги", "услуги")
        improved_query = improved_query.replace("как как", "как")
        improved_query = improved_query.replace("что что", "что")
        
        # Убираем лишние пробелы
        improved_query = " ".join(improved_query.split())
        
        if len(improved_query.split()) >= 2:  # Минимум 2 слова
            improved.append(improved_query)
    
    return improved
