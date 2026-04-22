# -*- coding: utf-8 -*-
"""
Async OpenAI-compatible client singleton with runtime guards.
Ensures responses.create() is available and async at startup.
Configured for OpenRouter-compatible Responses API with proper timeouts and retries.
"""
from __future__ import annotations
import os
import inspect
import logging
import httpx
from openai import AsyncOpenAI
from openai import __version__ as openai_version

log = logging.getLogger("llm")

_client: AsyncOpenAI | None = None

def get_async_client() -> AsyncOpenAI:
    """
    Get or create AsyncOpenAI client for OpenRouter/OpenAI-compatible endpoint
    with optimized timeouts and retries.
    
    HTTP timeouts:
    - connect: 10s (connection establishment)
    - write: 60s (request body write)
    - pool: 60s (connection pool)
    - read: 600s (response read - critical for long GPT-5 reasoning)
    
    Retries: 5 attempts with exponential backoff on 429/5xx/timeout/connection errors
    """
    global _client
    if _client is None:
        # Primary env contract
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        base_url = (
            os.environ.get("OPENAI_BASE_URL")
            or os.environ.get("OPENROUTER_BASE_URL")
            or "https://openrouter.ai/api/v1"
        )

        default_headers = {}
        site_url = os.environ.get("OPENROUTER_SITE_URL")
        site_name = os.environ.get("OPENROUTER_SITE_NAME")
        if site_url:
            default_headers["HTTP-Referer"] = site_url
        if site_name:
            default_headers["X-Title"] = site_name
        
        # Custom HTTP client with proper timeouts for GPT-5
        http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=10.0,   # Connection establishment
                write=60.0,     # Writing request body
                pool=60.0,      # Getting connection from pool
                read=600.0      # Reading response (10 mins for long generations)
            ),
            limits=httpx.Limits(
                max_keepalive_connections=20,
                max_connections=100,
                keepalive_expiry=30.0
            )
        )
        
        # Create client with proper retries and custom HTTP client
        _client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=http_client,
            max_retries=5,  # 5 retries with exponential backoff
            default_headers=default_headers or None,
        )
        
        # Runtime guards - verify responses.create() exists and is async
        has_responses = hasattr(_client, "responses")
        is_coro = has_responses and inspect.iscoroutinefunction(_client.responses.create)
        
        if not has_responses:
            raise RuntimeError(
                f"OpenAI SDK {openai_version}: AsyncOpenAI.responses not found"
            )
        
        if not is_coro:
            raise RuntimeError(
                f"OpenAI SDK {openai_version}: responses.create is not async"
            )
        
        log.info(
            "[LLM] OpenAI SDK %s; provider=openrouter-compatible; base_url=%s; "
            "AsyncOpenAI.responses.create OK (timeouts: connect=10s, write=60s, pool=60s, read=600s; retries=5)",
            openai_version,
            base_url,
        )
    
    return _client

# Export model setting for other modules to use.
# Primary: OPENAI_MODEL, fallback for legacy: OPENROUTER_MODEL.
OPENAI_MODEL = os.getenv("OPENAI_MODEL", os.getenv("OPENROUTER_MODEL", "openai/gpt-5.1"))
