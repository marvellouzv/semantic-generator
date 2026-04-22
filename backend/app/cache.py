# -*- coding: utf-8 -*-
"""
Redis кэширование для результатов OpenAI (опционально).
Если модуль redis отсутствует или сервер недоступен — кэш отключается.
"""
try:
    import redis  # type: ignore
except Exception:
    redis = None
import hashlib
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class SemanticCache:
    """Кэш для результатов семантической генерации"""
    
    def __init__(self, redis_url: Optional[str] = None):
        if redis is None:
            # Модуль не установлен — работаем без кэша
            self.enabled = False
            self.redis = None
            logger.warning("Redis module not installed. Cache disabled.")
            return

        if redis_url is None:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        
        try:
            self.redis = redis.from_url(redis_url, decode_responses=True)
            # Проверяем подключение
            self.redis.ping()
            self.enabled = True
            logger.info("Redis cache connected")
        except Exception as e:
            logger.warning(f"Redis unavailable: {e}. Cache disabled.")
            self.enabled = False
            self.redis = None
    
    def get_cache_key(self, request_type: str, **params) -> str:
        """Генерируем уникальный ключ из параметров запроса"""
        # Убираем параметры, которые не влияют на результат
        cache_params = {k: v for k, v in params.items() if k != 'template_id'}
        
        key_str = f"{request_type}:{json.dumps(cache_params, sort_keys=True)}"
        key_hash = hashlib.md5(key_str.encode()).hexdigest()
        return f"semantic:{request_type}:{key_hash}"
    
    def get(self, request_type: str, **params) -> Optional[Dict[str, Any]]:
        """Получить результат из кэша"""
        if not self.enabled:
            return None
        
        try:
            key = self.get_cache_key(request_type, **params)
            cached = self.redis.get(key)
            
            if cached:
                logger.debug(f"🎯 Cache hit: {key}")
                return json.loads(cached)
            
            logger.debug(f"❌ Cache miss: {key}")
            return None
        except Exception as e:
            logger.error(f"Ошибка при чтении из кэша: {e}")
            return None
    
    def set(self, request_type: str, data: Dict[str, Any], ttl_days: int = 7, **params) -> bool:
        """Сохранить результат в кэш"""
        if not self.enabled:
            return False
        
        try:
            key = self.get_cache_key(request_type, **params)
            ttl_seconds = ttl_days * 86400
            
            self.redis.setex(
                key,
                ttl_seconds,
                json.dumps(data)
            )
            
            logger.debug(f"💾 Cached: {key} (TTL: {ttl_days} дней)")
            return True
        except Exception as e:
            logger.error(f"Ошибка при записи в кэш: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """Очистить кэш по паттерну"""
        if not self.enabled:
            return 0
        
        try:
            keys = self.redis.keys(pattern)
            if keys:
                return self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Ошибка при очистке кэша: {e}")
            return 0
    
    def clear_all(self) -> bool:
        """Очистить весь кэш"""
        if not self.enabled:
            return False
        
        try:
            self.redis.flushdb()
            logger.info("🗑️ Весь кэш очищен")
            return True
        except Exception as e:
            logger.error(f"Ошибка при полной очистке кэша: {e}")
            return False

# Глобальный экземпляр кэша
cache = SemanticCache()
