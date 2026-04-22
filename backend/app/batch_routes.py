"""
Batch Processing API Routes
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import FileResponse
import io
import uuid
import pandas as pd
import json
import logging
from typing import List, Dict, Any
import redis
import os
from .celery_app import celery_app, process_topic_batch, aggregate_batch_results

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/batch", tags=["batch"])

# Redis для хранения метаданных батча
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
BATCH_THRESHOLD = int(os.getenv("BATCH_THRESHOLD", "20"))

try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
except:
    redis_client = None
    logger.warning("Redis not available for batch processing")

@router.post("/upload")
async def upload_batch_file(file: UploadFile = File(...)):
    """Загрузить CSV/XLSX файл для batch обработки"""
    
    if not redis_client:
        raise HTTPException(status_code=500, detail="Batch processing service not available")
    
    try:
        # Парсим файл
        if file.filename.endswith('.xlsx'):
            df = pd.read_excel(file.file)
        elif file.filename.endswith('.csv'):
            df = pd.read_csv(file.file)
        else:
            raise HTTPException(status_code=400, detail="Only CSV and XLSX files supported")
        
        # Валидируем столбцы
        if 'topic' not in df.columns:
            raise HTTPException(status_code=400, detail="File must have 'topic' column")
        
        # Создаем batch ID
        batch_id = str(uuid.uuid4())
        
        # Парсим данные
        topics_data = []
        for _, row in df.iterrows():
            topic = str(row.get('topic', '')).strip()
            
            if not topic:
                continue
            
            # Парсим интенты (могут быть разделены запятой или точкой с запятой)
            intents_raw = str(row.get('intents', 'commercial,informational'))
            intents = [i.strip() for i in intents_raw.replace(';', ',').split(',') if i.strip()]
            
            topics_data.append({
                'topic': topic,
                'intents': intents or ['commercial', 'informational']
            })
        
        if not topics_data:
            raise HTTPException(status_code=400, detail="No valid topics found in file")
        
        # Определяем, использовать ли batch обработку
        use_batch = len(topics_data) >= BATCH_THRESHOLD
        
        # Создаем задачи Celery
        task_ids = []
        for topic_data in topics_data:
            task = process_topic_batch.delay(
                topic=topic_data['topic'],
                intents=topic_data['intents'],
                batch_id=batch_id
            )
            task_ids.append(task.id)
        
        # Сохраняем метаданные батча в Redis
        batch_metadata = {
            'id': batch_id,
            'filename': file.filename,
            'total_topics': len(topics_data),
            'task_ids': json.dumps(task_ids),
            'status': 'processing',
            'use_batch': use_batch,
            'created_at': pd.Timestamp.now().isoformat()
        }
        
        redis_client.setex(
            f"batch:{batch_id}",
            86400,  # 24 часа TTL
            json.dumps(batch_metadata)
        )
        
        logger.info(f"[BATCH {batch_id}] Created with {len(topics_data)} topics, "
                   f"use_batch: {use_batch}")
        
        return {
            "batch_id": batch_id,
            "total_topics": len(topics_data),
            "use_batch": use_batch,
            "status": "processing"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading batch file: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/jobs/{batch_id}")
async def get_batch_status(batch_id: str):
    """Получить статус batch job"""
    
    if not redis_client:
        raise HTTPException(status_code=500, detail="Batch processing service not available")
    
    try:
        batch_data = redis_client.get(f"batch:{batch_id}")
        
        if not batch_data:
            raise HTTPException(status_code=404, detail="Batch job not found")
        
        batch_metadata = json.loads(batch_data)
        task_ids = json.loads(batch_metadata['task_ids'])
        
        # Проверяем статус всех задач
        completed = 0
        failed = 0
        pending = 0
        
        for task_id in task_ids:
            task = celery_app.AsyncResult(task_id)
            
            if task.ready():
                completed += 1
                if task.failed():
                    failed += 1
            else:
                pending += 1
        
        progress = (completed / len(task_ids) * 100) if task_ids else 0
        
        return {
            "batch_id": batch_id,
            "filename": batch_metadata['filename'],
            "total": len(task_ids),
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "progress": f"{progress:.1f}%",
            "status": "completed" if completed == len(task_ids) else "processing"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting batch status: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/jobs/{batch_id}/results")
async def get_batch_results(batch_id: str):
    """Получить результаты batch job"""
    
    if not redis_client:
        raise HTTPException(status_code=500, detail="Batch processing service not available")
    
    try:
        batch_data = redis_client.get(f"batch:{batch_id}")
        
        if not batch_data:
            raise HTTPException(status_code=404, detail="Batch job not found")
        
        batch_metadata = json.loads(batch_data)
        task_ids = json.loads(batch_metadata['task_ids'])
        
        # Собираем результаты
        results = []
        successful = 0
        failed = 0
        
        for task_id in task_ids:
            task = celery_app.AsyncResult(task_id)
            
            if task.ready():
                result = task.result
                results.append(result)
                
                if result.get('status') == 'success':
                    successful += 1
                else:
                    failed += 1
        
        return {
            "batch_id": batch_id,
            "filename": batch_metadata['filename'],
            "results": results,
            "summary": {
                "total": len(task_ids),
                "successful": successful,
                "failed": failed,
                "total_clusters": sum(r.get('cluster_count', 0) for r in results)
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting batch results: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/jobs/{batch_id}/export")
async def export_batch_results(
    batch_id: str,
    format: str = Query("xlsx", regex="^(xlsx|csv|json)$")
):
    """Экспортировать результаты batch в XLSX/CSV/JSON"""
    
    if not redis_client:
        raise HTTPException(status_code=500, detail="Batch processing service not available")
    
    try:
        batch_data = redis_client.get(f"batch:{batch_id}")
        
        if not batch_data:
            raise HTTPException(status_code=404, detail="Batch job not found")
        
        batch_metadata = json.loads(batch_data)
        task_ids = json.loads(batch_metadata['task_ids'])
        
        # Собираем все кластеры
        all_clusters = []
        
        for task_id in task_ids:
            task = celery_app.AsyncResult(task_id)
            
            if task.ready():
                result = task.result
                
                if result.get('status') == 'success':
                    topic = result.get('topic')
                    
                    for cluster in result.get('clusters', []):
                        cluster_export = cluster.copy() if isinstance(cluster, dict) else cluster.model_dump()
                        cluster_export['topic'] = topic
                        all_clusters.append(cluster_export)
        
        if not all_clusters:
            raise HTTPException(status_code=400, detail="No completed results to export")
        
        # Создаем DataFrame
        df = pd.DataFrame(all_clusters)
        
        # Экспортируем в нужном формате
        if format == 'csv':
            output = io.StringIO()
            df.to_csv(output, index=False, encoding='utf-8')
            output.seek(0)
            
            return {
                "data": output.getvalue(),
                "filename": f"batch_results_{batch_id}.csv"
            }
        
        elif format == 'json':
            return {
                "data": df.to_json(orient='records'),
                "filename": f"batch_results_{batch_id}.json"
            }
        
        else:  # xlsx
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Clusters', index=False)
            output.seek(0)
            
            return {
                "data": output.getvalue().hex(),  # Encoding binary data
                "filename": f"batch_results_{batch_id}.xlsx",
                "binary": True
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting batch results: {e}")
        raise HTTPException(status_code=400, detail=str(e))
