"""
MCP Gateway для OpenAI через openai-guard сервер.

Использование:
    from app.mcp_gate import call_openai_via_mcp

    response = await call_openai_via_mcp(
        model="gpt-5",
        messages=[{"role": "user", "content": "Hello!"}],
        max_output_tokens=1000
    )
"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def call_openai_via_mcp(
    model: str,
    messages: List[Dict[str, Any]],
    max_output_tokens: int = 8192,
    instructions: Optional[str] = None,
) -> str:
    """
    Вызывает OpenAI через MCP-сервер openai-guard.
    
    Args:
        model: Название модели (gpt-5, gpt-5-mini, gpt-4o и т.д.)
        messages: Список сообщений в формате OpenAI Chat API
        max_output_tokens: Максимальное количество токенов ответа
        instructions: Опциональные системные инструкции
    
    Returns:
        Текст ответа от модели
    
    Raises:
        RuntimeError: Если MCP-вызов не удался
    
    Notes:
        - Для моделей gpt-5* автоматически фильтруются запрещённые параметры
        - Поддерживает только: model, messages/input, max_output_tokens, instructions
        - НЕ поддерживает: temperature, top_p, stop, verbosity, response_format
    """
    
    # Валидация для GPT-5
    if model.startswith("gpt-5"):
        logger.info(f"GPT-5 модель обнаружена: {model}. Применяются ограничения параметров.")
    
    # Формируем payload для MCP
    payload = {
        "model": model,
        "messages": messages,
        "max_output_tokens": max_output_tokens,
    }
    
    if instructions:
        payload["instructions"] = instructions
    
    logger.info(f"MCP call → {model}, messages={len(messages)}, max_tokens={max_output_tokens}")
    
    # TODO: Здесь должен быть реальный вызов MCP-инструмента через Cursor runtime
    # Для интеграции в продакшн нужно использовать MCP Python SDK или HTTP транспорт
    # Пока возвращаем заглушку с описанием
    
    raise NotImplementedError(
        "MCP integration stub. "
        "Для работы нужно:\n"
        "1. Установить mcp Python SDK: pip install mcp\n"
        "2. Инициализировать MCP клиент со stdio транспортом\n"
        "3. Вызвать tool 'ask-openai' с payload\n"
        "4. Распарсить response.content[0].text\n\n"
        "Альтернатива: использовать существующий gpt5_wrapper.py с ask_gpt5()"
    )


async def responses_create(
    model: str,
    input_blocks: List[Dict[str, Any]],
    max_output_tokens: int = 8192,
) -> str:
    """
    Альтернативный вариант вызова в стиле Responses API.
    
    Args:
        model: Название модели
        input_blocks: Блоки ввода в формате [{role, content: [{type, text}]}]
        max_output_tokens: Максимум токенов
    
    Returns:
        Текст ответа
    """
    # Конвертируем input_blocks в messages для OpenAI
    messages = []
    for block in input_blocks:
        role = block.get("role", "user")
        content_items = block.get("content", [])
        
        # Собираем текст из всех content items
        text_parts = []
        for item in content_items:
            if isinstance(item, dict) and item.get("type") in ["input_text", "text"]:
                text_parts.append(item.get("text", ""))
            elif isinstance(item, str):
                text_parts.append(item)
        
        messages.append({
            "role": role,
            "content": " ".join(text_parts)
        })
    
    return await call_openai_via_mcp(
        model=model,
        messages=messages,
        max_output_tokens=max_output_tokens
    )


# Для обратной совместимости с существующим кодом
async def ask_gpt5_mcp(
    input_blocks: List[Dict[str, Any]],
    *,
    model: str = "gpt-5",
    max_output_tokens: int = 1200,
) -> str:
    """
    Drop-in replacement для app.gpt5_wrapper.ask_gpt5.
    
    Вызывает OpenAI через MCP вместо прямого SDK.
    """
    return await responses_create(
        model=model,
        input_blocks=input_blocks,
        max_output_tokens=max_output_tokens
    )

