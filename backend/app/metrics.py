# -*- coding: utf-8 -*-
"""
Метрики и статистика использования API
"""
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
import os
from pathlib import Path

logger = logging.getLogger(__name__)

class MetricsCollector:
    """Сборщик метрик использования API"""
    
    def __init__(self, db_path: str = "metrics.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Инициализируем БД метрик"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        endpoint TEXT NOT NULL,
                        status INTEGER NOT NULL,
                        duration_ms REAL NOT NULL,
                        openai_cost REAL DEFAULT 0,
                        tokens_used INTEGER DEFAULT 0,
                        topic TEXT,
                        intents TEXT
                    )
                """)
                
                # Индексы для быстрого поиска
                conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON metrics(timestamp)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_endpoint ON metrics(endpoint)")
                conn.commit()
                
            logger.info("✅ Таблица метрик инициализирована")
        except Exception as e:
            logger.error(f"Ошибка инициализации БД метрик: {e}")
    
    def record(self, endpoint: str, status: int, duration_ms: float, 
               openai_cost: float = 0, tokens_used: int = 0,
               topic: str = None, intents: List[str] = None):
        """Записать метрику"""
        try:
            intents_str = json.dumps(intents) if intents else None
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO metrics 
                    (endpoint, status, duration_ms, openai_cost, tokens_used, topic, intents)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (endpoint, status, duration_ms, openai_cost, tokens_used, topic, intents_str))
                conn.commit()
        except Exception as e:
            logger.error(f"Ошибка при записи метрики: {e}")
    
    def get_stats_for_days(self, days: int = 7) -> Dict[str, Any]:
        """Получить статистику за последние N дней"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
                
                # Основная статистика
                stats = conn.execute("""
                    SELECT 
                        COUNT(*) as count,
                        SUM(CASE WHEN status >= 200 AND status < 300 THEN 1 ELSE 0 END) as success_count,
                        AVG(duration_ms) as avg_duration,
                        SUM(openai_cost) as total_cost,
                        SUM(tokens_used) as total_tokens
                    FROM metrics
                    WHERE timestamp >= ?
                """, (start_date,)).fetchone()
                
                total = stats['count'] or 0
                success = stats['success_count'] or 0
                
                # Топ темы
                top_topics = conn.execute("""
                    SELECT topic, COUNT(*) as count
                    FROM metrics
                    WHERE timestamp >= ? AND topic IS NOT NULL
                    GROUP BY topic
                    ORDER BY count DESC
                    LIMIT 10
                """, (start_date,)).fetchall()
                
                # Ошибки
                errors = conn.execute("""
                    SELECT status, COUNT(*) as count
                    FROM metrics
                    WHERE timestamp >= ? AND (status < 200 OR status >= 300)
                    GROUP BY status
                """, (start_date,)).fetchall()
                
                return {
                    "period_days": days,
                    "count": total,
                    "success_rate": (success / total * 100) if total > 0 else 0,
                    "avg_duration": stats['avg_duration'] or 0,
                    "total_cost": stats['total_cost'] or 0,
                    "total_tokens": stats['total_tokens'] or 0,
                    "top_topics": [{"topic": row['topic'], "count": row['count']} 
                                   for row in top_topics],
                    "errors": [{"status": row['status'], "count": row['count']} 
                               for row in errors]
                }
        except Exception as e:
            logger.error(f"Ошибка при получении статистики: {e}")
            return {}
    
    def get_today_stats(self) -> Dict[str, Any]:
        """Получить статистику за сегодня"""
        return self.get_stats_for_days(days=1)
    
    def get_hourly_stats(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Получить почасовую статистику"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                start_time = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
                
                hourly = conn.execute("""
                    SELECT 
                        strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
                        COUNT(*) as count,
                        SUM(CASE WHEN status >= 200 AND status < 300 THEN 1 ELSE 0 END) as success_count,
                        AVG(duration_ms) as avg_duration,
                        SUM(openai_cost) as total_cost
                    FROM metrics
                    WHERE timestamp >= ?
                    GROUP BY hour
                    ORDER BY hour DESC
                """, (start_time,)).fetchall()
                
                return [dict(row) for row in hourly]
        except Exception as e:
            logger.error(f"Ошибка при получении почасовой статистики: {e}")
            return []
    
    def cleanup_old_metrics(self, days: int = 90):
        """Удалить старые метрики (старше N дней)"""
        try:
            cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM metrics WHERE timestamp < ?",
                    (cutoff_date,)
                )
                conn.commit()
                
                logger.info(f"🗑️ Удалено {cursor.rowcount} старых метрик")
        except Exception as e:
            logger.error(f"Ошибка при очистке метрик: {e}")

# Глобальный экземпляр сборщика метрик
metrics_collector = MetricsCollector()
