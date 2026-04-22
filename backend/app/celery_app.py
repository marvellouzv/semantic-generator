# -*- coding: utf-8 -*-
"""
Celery Configuration и Tasks для Batch обработки
"""
from celery import Celery, Task
import os
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

# Конфигурация Celery
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

class ContextTask(Task):
    """Celery Task с контекстом приложения"""
    def __call__(self, *args, **kwargs):
        return self.run(*args, **kwargs)

celery_app = Celery(
    "semantic_generator",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
)

# Инициализируем OpenAI client
from .gpt5_head_queries import generate_clusters_gpt5

# Note: OpenAI client is managed by ask_gpt5() wrapper; no local client needed here

@celery_app.task(bind=True, base=ContextTask)
def process_topic_batch(self, topic: str, intents: list, batch_id: str):
    """
    Фоновая задача для обработки одной темы в batch
    
    Args:
        topic: Тема для генерации
        intents: Список интентов
        batch_id: ID батча для группировки
    
    Returns:
        Dict с результатами генерации
    """
    try:
        logger.info(f"[BATCH {batch_id}] Processing topic: {topic}")
        
        # Celery tasks run in sync context, but we need to call async functions
        # Use asyncio.run() instead of run_until_complete (Python 3.7+)
        import asyncio
        
        clusters = asyncio.run(
            generate_clusters_gpt5(
                topic=topic,
                selected_intents=intents,
                target_count=0,
                brand_whitelist=None,
                use_ensemble=True
            )
        )
        
        logger.info(f"[BATCH {batch_id}] Generated {len(clusters) if clusters else 0} clusters for {topic}")
        
        return {
            'topic': topic,
            'status': 'success',
            'cluster_count': len(clusters) if clusters else 0,
            'clusters': clusters or []
        }
    
    except Exception as e:
        logger.error(f"[BATCH {batch_id}] Error processing {topic}: {str(e)}")
        return {
            'topic': topic,
            'status': 'error',
            'error': str(e),
            'cluster_count': 0,
            'clusters': []
        }

@celery_app.task
def aggregate_batch_results(batch_id: str, task_ids: list):
    """
    Агрегирует результаты из всех задач батча
    """
    from celery.result import AsyncResult
    
    results = []
    total_clusters = 0
    failed_count = 0
    
    for task_id in task_ids:
        try:
            result = AsyncResult(task_id, app=celery_app).get(timeout=30)
            results.append(result)
            
            if result.get('status') == 'success':
                total_clusters += result.get('cluster_count', 0)
            else:
                failed_count += 1
        except Exception as e:
            logger.error(f"Error getting result for task {task_id}: {e}")
            failed_count += 1
    
    logger.info(f"[BATCH {batch_id}] Aggregation complete: {len(results)} topics, "
                f"{total_clusters} total clusters, {failed_count} failed")
    
    return {
        'batch_id': batch_id,
        'total_topics': len(task_ids),
        'successful_topics': len(task_ids) - failed_count,
        'failed_topics': failed_count,
        'total_clusters': total_clusters,
        'results': results
    }
