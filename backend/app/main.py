# -*- coding: utf-8 -*-
import sys
import io

# Force UTF-8 encoding for Windows console
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
import os, asyncio, httpx, json, time
from dotenv import load_dotenv

from .models import UpperGraphRequest, UpperGraph, CreateTemplateRequest, TemplateListResponse, ClusterTemplate
from .deterministic_generator import expand_deterministic_fallback
from .gpt_cleanup import cleanup_all_queries, improve_deterministic_quality
from .gpt5_head_queries import generate_clusters_gpt5, expand_template_with_gpt5
from .llm_stage2 import expand_stage2
from . import templates_storage
from . import history_storage
from .cache import cache
from .metrics import metrics_collector

load_dotenv()

# LLM provider configuration (OpenAI-compatible API, e.g. OpenRouter)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", os.getenv("OPENROUTER_MODEL", "openai/gpt-5.1"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", os.getenv("OPENROUTER_API_KEY", ""))
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"))
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "600"))
USE_GPT5_ENSEMBLE = os.getenv("USE_GPT5_ENSEMBLE", "true").lower() == "true"

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is required for LLM calls")

print(f"[SECURE] Using LLM model: {OPENAI_MODEL}")
print(f"[SECURE] LLM base URL: {OPENAI_BASE_URL}")

# Migrate legacy templates on startup
try:
    migrated = templates_storage.migrate_legacy_templates()
    if migrated:
        print(f"[TEMPLATES] Migrated {migrated} legacy template(s)")
except Exception as _:
    pass

# Remove direct client usage; use ask_gpt5 wrapper and internal singleton

app = FastAPI(title="Semantic Generator Starter")
try:
    from .health_llm import router as health_router
    app.include_router(health_router)
except Exception:
    pass

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware для сбора метрик
@app.middleware("http")
async def metrics_middleware(request, call_next):
    """Собирает метрики для каждого запроса"""
    start_time = time.time()
    
    try:
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        
        # Извлекаем информацию из request
        endpoint = request.url.path
        status = response.status_code
        
        # Пытаемся получить тему и интенты (если они были в body)
        topic = None
        intents = None
        
        try:
            if request.method == "POST" and "/upper-graph" in endpoint:
                # Для /api/v1/upper-graph пытаемся получить параметры
                body = await request.body()
                if body:
                    data = json.loads(body)
                    topic = data.get("topic")
                    intents = data.get("intents")
        except:
            pass
        
        # Записываем метрику
        metrics_collector.record(
            endpoint=endpoint,
            status=status,
            duration_ms=duration_ms,
            topic=topic,
            intents=intents
        )
        
        return response
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        metrics_collector.record(
            endpoint=request.url.path,
            status=500,
            duration_ms=duration_ms
        )
        raise

class Health(BaseModel):
    status: str = "ok"

class SaveHistoryRequest(BaseModel):
    topic: str
    intents: List[str] = Field(default_factory=list)
    locale: str = "ru"
    upperGraph: dict = Field(default_factory=dict)
    generationTime: int = 0

@app.get("/health", response_model=Health)
async def health():
    return Health()

# Load schemas and prompts
SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "schema")
PROMPT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "prompts")

with open(os.path.join(SCHEMA_DIR, "upper_graph.schema.json"), "r", encoding="utf-8") as f:
    UPPER_SCHEMA = json.load(f)

@app.get("/api/v1/health")
def health_check():
    return {"ok": True, "model": OPENAI_MODEL, "status": "ready"}

@app.post("/api/v1/upper-graph", response_model=UpperGraph)
async def upper_graph(req: UpperGraphRequest):
    """Генерация кластеров с кэшированием результатов"""
    print(f"[REQUEST] Processing: topic='{req.topic}', intents={req.intents}")
    
    try:
        # For OpenRouter, model ids can include provider prefix, e.g. openai/gpt-5.
        if "gpt-5" not in OPENAI_MODEL.lower():
            raise HTTPException(
                status_code=500,
                detail=f"Invalid model configuration: {OPENAI_MODEL}. Expected GPT-5 family model (e.g. openai/gpt-5)."
            )
        
        # Проверяем кэш только для обычных запросов (без template_id)
        if not req.template_id:
            cache_params = {
                "topic": req.topic,
                "intents": tuple(sorted(req.intents)),
                "locale": req.locale,
                "minus_words": tuple(sorted(req.minus_words or [])),
                "regions": tuple(sorted(req.regions or [])),
            }
            
            cached_result = cache.get("upper_graph", **cache_params)
            if cached_result:
                print(f"[CACHE HIT] Cached result for: {req.topic}")
                return UpperGraph(**cached_result)
        
        # Проверяем режим дополнения шаблона
        if req.template_id:
            print(f"Template expansion mode: template_id = {req.template_id}")
            
            # Загружаем шаблон
            template = templates_storage.load_template(req.template_id)
            if not template:
                raise HTTPException(status_code=404, detail="Template not found")
            
            print(f"Expanding template '{template.name}' with {len(template.clusters)} existing clusters")
            
            # Генерируем новые кластеры для дополнения
            new_clusters = await expand_template_with_gpt5(
                template=template,
                selected_intents=req.intents,
                minus_words=req.minus_words,
                regions=req.regions,
            )
            
            if not new_clusters:
                # Если новых кластеров нет, возвращаем исходный шаблон
                print("No new clusters generated, returning original template")
                clusters = [cluster.model_dump() for cluster in template.clusters]
            else:
                # Объединяем существующие и новые кластеры
                existing_clusters = [cluster.model_dump() for cluster in template.clusters]
                all_clusters = existing_clusters + new_clusters
                
                # Нормализация и дедупликация
                from .query_normalizer import normalize_and_deduplicate_clusters
                clusters = normalize_and_deduplicate_clusters(all_clusters)
                
                print(f"Template expanded: {len(template.clusters)} + {len(new_clusters)} = {len(clusters)} clusters (after deduplication)")
        else:
            # No limits - maximum coverage mode
            
            # Генерация кластеров с максимальным покрытием
            print(f"Generating clusters with maximum coverage")
            
            clusters = await generate_clusters_gpt5(
                topic=req.topic,
                selected_intents=req.intents,
                target_count=0,  # 0 = без ограничений, максимальное покрытие
                minus_words=req.minus_words,
                regions=req.regions,
                use_ensemble=USE_GPT5_ENSEMBLE
            )
            
            print(f"Generated {len(clusters) if clusters else 0} clusters")
        
        # Если GPT не сработал, возвращаем ошибку
        if not clusters:
            print("GPT-5 generation failed: no clusters generated")
            raise HTTPException(status_code=500, detail="GPT-5 generation failed. Please try again.")
        
        result = {
            "topic": req.topic,
            "locale": req.locale,
            "intents_applied": req.intents,
            "clusters": clusters
        }
        print(f"Generated {len(clusters)} clusters with GPT-5")
        
        # Сохраняем в кэш для обычных запросов (не шаблонов)
        if not req.template_id:
            cache_params = {
                "topic": req.topic,
                "intents": tuple(sorted(req.intents)),
                "locale": req.locale,
                "minus_words": tuple(sorted(req.minus_words or [])),
                "regions": tuple(sorted(req.regions or [])),
            }
            cache.set("upper_graph", result, ttl_days=7, **cache_params)
            print(f"[CACHE SET] Result cached for: {req.topic}")
        
        print(f"Final result: {len(result.get('clusters', []))} clusters")
        return UpperGraph(**result)
        
    except HTTPException as http_exc:  # пробрасываем как есть, чтобы не терять детали
        raise http_exc
    except Exception as e:
        # Детальная обработка ошибок для диагностики
        import traceback
        from datetime import datetime
        
        error_details = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "model_used": OPENAI_MODEL,
            "timestamp": str(datetime.now()),
            "traceback": traceback.format_exc()
        }
        
        # Если это ошибка LLM-провайдера, извлекаем детали
        if hasattr(e, 'response'):
            error_details["openai_status"] = getattr(e.response, 'status_code', None)
            error_details["openai_data"] = getattr(e.response, 'data', None)
        
        print("DETAILED ERROR in upper_graph:")
        print(f"   Type: {error_details['error_type']}")
        print(f"   Message: {error_details['error_message']}")
        print(f"   Model: {error_details['model_used']}")
        # Безопасный вывод traceback без эмодзи
        traceback_text = error_details['traceback'].encode('ascii', 'replace').decode('ascii')
        print(f"   Traceback: {traceback_text}")
        
        # Возвращаем читаемую ошибку для пользователя + детали для отладки
        user_message = f"GPT generation failed: {error_details['error_message']}"
        
        # Для некоторых типичных ошибок даем понятные объяснения
        if "401" in str(e) or "authentication" in str(e).lower():
            user_message = "Ошибка аутентификации провайдера LLM. Проверьте API ключ."
        elif "quota" in str(e).lower() or "billing" in str(e).lower():
            user_message = "Превышена квота провайдера LLM или проблемы с биллингом."
        elif "model" in str(e).lower() and "not found" in str(e).lower():
            user_message = f"Модель '{OPENAI_MODEL}' недоступна. Проверьте доступ к модели в вашем LLM-провайдере."
        elif "timeout" in str(e).lower():
            user_message = "Таймаут запроса к LLM-провайдеру. Попробуйте еще раз."
        
        # В detail отдадим подробности, чтобы фронт и разработчик видели первопричину
        raise HTTPException(status_code=500, detail={
            "message": user_message,
            "details": error_details
        })


@app.post("/api/v1/expand-queries")
async def expand_queries(req: dict):
    """Расширение запросов на втором этапе с использованием JSON schema"""
    try:
        topic = req.get("topic", "")
        locale = req.get("locale", "ru-RU")
        additional_requirements = req.get("additional_requirements", "")
        existing_queries = req.get("existing_queries", [])
        parent_themes = req.get("parent_themes", [])
        allowed_types = req.get("allowed_types", ["commercial", "informational", "service", "price", "local"])
        minus_words = req.get("minus_words", [])
        regions = req.get("regions", [])
        
        if not topic or not additional_requirements:
            raise HTTPException(status_code=400, detail="Topic and additional_requirements are required")
        
        print(f"[API] Expanding queries for topic: {topic}")
        print(f"[API] Additional requirements: {additional_requirements}")
        print(f"[API] Existing queries: {len(existing_queries)}")
        print(f"[API] Parent themes: {len(parent_themes)}")
        print(f"[API] Allowed types: {allowed_types}")
        
        # Группируем существующие запросы по Parent Theme
        existing_by_parent = {}
        for query in existing_queries:
            # Простая группировка - в реальности можно улучшить
            for theme in parent_themes:
                if theme not in existing_by_parent:
                    existing_by_parent[theme] = []
                existing_by_parent[theme].append(query)
        
        # Генерируем дополнительные запросы с помощью нового модуля
        # Увеличиваем target_count для более богатого расширения
        rows = await expand_stage2(
            topic=topic,
            allowed_types=allowed_types,
            user_notes=additional_requirements,
            parent_themes=parent_themes,
            existing_by_parent=existing_by_parent,
            target_count=50,  # Увеличено с 15 до 50 для более полного покрытия
            minus_words=minus_words,
            regions=regions,
        )
        
        # Конвертируем в формат, ожидаемый фронтендом
        expanded_queries = []
        for row in rows:
            expanded_queries.append({
                "query": row["Head Query"],
                "intent": row["Intent"],
                "demand_level": row["Demand Level"],
                "parent_theme": row["Parent Theme"],
                "tags": []  # Пока пустые теги
            })
        
        print(f"[API] Generated {len(expanded_queries)} additional queries")
        
        return {
            "topic": topic,
            "locale": locale,
            "additional_requirements": additional_requirements,
            "expanded_queries": expanded_queries
        }
        
    except Exception as e:
        print(f"Error in expand_queries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/export")
async def export_data(req: dict):
    """Export expanded queries to XLSX or CSV format."""
    from fastapi.responses import StreamingResponse
    import pandas as pd
    import io
    
    format_type = req.get("format", "xlsx").lower()
    data = req.get("data", {})
    
    # Convert expanded queries to flat structure
    rows = []
    expanded = data.get("expanded", [])
    for cluster in expanded:
        cluster_name = cluster.get("cluster_name", "")
        cluster_id = cluster.get("cluster_id", "")
        for query in cluster.get("queries", []):
            rows.append({
                "cluster_id": cluster_id,
                "cluster_name": cluster_name,
                "query": query.get("q", ""),
                "intent": query.get("intent", ""),
                "tags": ", ".join(query.get("tags", []))
            })
    
    df = pd.DataFrame(rows)
    
    if format_type == "csv":
        output = io.StringIO()
        df.to_csv(output, index=False, encoding='utf-8')
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8')),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=semantic_queries.csv"}
        )
    else:  # xlsx
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Queries', index=False)
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=semantic_queries.xlsx"}
        )

@app.post("/api/v1/export-clusters")
async def export_clusters(req: dict):
    """Export clusters to XLSX or CSV format."""
    from fastapi.responses import StreamingResponse
    import pandas as pd
    import io
    
    format_type = req.get("format", "xlsx").lower()
    clusters = req.get("clusters", [])
    
    # Convert clusters to flat structure
    rows = []
    for cluster in clusters:
        # Основная информация о кластере
        cluster_data = {
            "cluster_id": cluster.get("cluster_id", ""),
            "name": cluster.get("name", ""),
            "gpt_intent": cluster.get("gpt_intent", ""),
            "demand_level": cluster.get("demand_level", ""),
            "parent_theme": cluster.get("parent_theme", ""),
            "intent_mix": ", ".join(cluster.get("intent_mix", [])),
            "tags": ", ".join(cluster.get("tags", [])),
            "notes": cluster.get("notes", ""),
            "seed_examples": ", ".join(cluster.get("seed_examples", []))
        }
        rows.append(cluster_data)
    
    df = pd.DataFrame(rows)
    
    if format_type == "csv":
        output = io.StringIO()
        df.to_csv(output, index=False, encoding='utf-8')
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8')),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=clusters.csv"}
        )
    else:  # xlsx
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Clusters', index=False)
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=clusters.xlsx"}
        )


# ============== TEMPLATES API ==============

@app.post("/api/v1/history")
def save_history_generation(request: SaveHistoryRequest):
    """Сохранить генерацию в историю на диске."""
    try:
        item = history_storage.save_generation(
            topic=request.topic,
            intents=request.intents,
            locale=request.locale,
            upper_graph=request.upperGraph,
            generation_time=request.generationTime,
        )
        return item
    except Exception as e:
        print(f"Error saving history generation: {e}")
        raise HTTPException(status_code=500, detail="Failed to save history generation")

@app.get("/api/v1/history")
def list_history_generations():
    """Получить всю историю генераций."""
    try:
        return {"generations": history_storage.list_generations()}
    except Exception as e:
        print(f"Error listing history generations: {e}")
        raise HTTPException(status_code=500, detail="Failed to list history generations")

@app.get("/api/v1/history/{generation_id}")
def get_history_generation(generation_id: str):
    """Получить одну генерацию из истории."""
    item = history_storage.get_generation(generation_id)
    if not item:
        raise HTTPException(status_code=404, detail="History generation not found")
    return item

@app.post("/api/v1/history/{generation_id}/restore")
def restore_history_generation(generation_id: str):
    """Сделать генерацию активной и вернуть ее содержимое."""
    item = history_storage.restore_generation(generation_id)
    if not item:
        raise HTTPException(status_code=404, detail="History generation not found")
    return {"upperGraph": item.get("upperGraph"), "generation": item}

@app.delete("/api/v1/history/{generation_id}")
def delete_history_generation(generation_id: str):
    """Удалить генерацию из истории."""
    deleted = history_storage.delete_generation(generation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="History generation not found")
    return {"message": "History generation deleted"}

@app.post("/api/v1/history/import")
def import_history_generations(payload: dict):
    """Импорт истории генераций из JSON."""
    generations = payload.get("generations")
    if not isinstance(generations, list):
        raise HTTPException(status_code=400, detail="Invalid import payload")

    imported = 0
    for generation in generations:
        if not isinstance(generation, dict):
            continue
        try:
            metadata = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
            history_storage.save_generation(
                topic=str(generation.get("topic", "")).strip() or "Без темы",
                intents=[str(i) for i in generation.get("intents", []) if isinstance(i, str)],
                locale=str(generation.get("locale", "ru")) or "ru",
                upper_graph=generation.get("upperGraph") if isinstance(generation.get("upperGraph"), dict) else {},
                generation_time=int(metadata.get("generationTime", 0) or 0),
            )
            imported += 1
        except Exception:
            continue

    return {"imported": imported}

@app.post("/api/v1/templates", response_model=ClusterTemplate)
def create_template(request: CreateTemplateRequest):
    """Создать новый шаблон кластеров."""
    try:
        template = templates_storage.save_template(request)
        return template
    except Exception as e:
        print(f"Error creating template: {e}")
        raise HTTPException(status_code=500, detail="Failed to create template")

@app.get("/api/v1/templates", response_model=TemplateListResponse)
def list_templates():
    """Получить список всех шаблонов."""
    try:
        templates = templates_storage.list_templates()
        return TemplateListResponse(templates=templates)
    except Exception as e:
        print(f"Error listing templates: {e}")
        raise HTTPException(status_code=500, detail="Failed to list templates")

@app.get("/api/v1/templates/{template_id}", response_model=ClusterTemplate)
def get_template(template_id: str):
    """Получить шаблон по ID."""
    template = templates_storage.load_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template

@app.get("/api/v1/templates/{template_id}/upper-graph", response_model=UpperGraph)
def get_template_as_upper_graph(template_id: str):
    """Получить шаблон в формате UpperGraph для использования."""
    template = templates_storage.load_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return templates_storage.template_to_upper_graph(template)

@app.delete("/api/v1/templates/{template_id}")
def delete_template(template_id: str):
    """Удалить шаблон."""
    success = templates_storage.delete_template(template_id)
    if not success:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"message": "Template deleted successfully"}


# ============== METRICS & STATS API ==============

@app.get("/api/v1/stats")
def get_stats(days: int = 7):
    """Получить статистику использования API за последние N дней"""
    stats = metrics_collector.get_stats_for_days(days=days)
    return {
        "period_days": days,
        "total_requests": stats.get("count", 0),
        "success_rate": f"{stats.get('success_rate', 0):.1f}%",
        "avg_response_time_ms": f"{stats.get('avg_duration', 0):.1f}",
        "total_llm_cost": f"${stats.get('total_cost', 0):.2f}",
        "total_openai_cost": f"${stats.get('total_cost', 0):.2f}",
        "tokens_consumed": stats.get("total_tokens", 0),
        "most_popular_topics": stats.get("top_topics", []),
        "errors_breakdown": stats.get("errors", [])
    }

@app.get("/api/v1/stats/today")
def get_today_stats():
    """Получить статистику за сегодня"""
    return get_stats(days=1)

@app.get("/api/v1/stats/hourly")
def get_hourly_stats(hours: int = 24):
    """Получить почасовую статистику"""
    hourly = metrics_collector.get_hourly_stats(hours=hours)
    return {
        "period_hours": hours,
        "hourly_data": hourly
    }

@app.post("/api/v1/stats/cleanup")
def cleanup_metrics(days: int = 90):
    """Очистить старые метрики (старше N дней)"""
    metrics_collector.cleanup_old_metrics(days=days)
    return {"message": f"Metrics older than {days} days cleaned"}
