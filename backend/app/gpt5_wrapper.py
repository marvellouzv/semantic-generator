# -*- coding: utf-8 -*-
"""
Unified wrapper for OpenRouter Responses API (OpenAI-compatible SDK).
- Input normalization: type:'text' → type:'input_text'
- Response format support with temperature guard
- Timing metrics and detailed error handling
- Always async/await (no sync/run_in_executor)
"""
from __future__ import annotations
import logging
import time
from typing import Any, Optional, Dict
from openai import BadRequestError, RateLimitError, APIError, APIConnectionError, APITimeoutError
from fastapi import HTTPException

from .openai_client import get_async_client, OPENAI_MODEL

log = logging.getLogger("llm")

def _normalize_input(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Auto-fix legacy type:'text' → type:'input_text'
    """
    out = []
    for msg in blocks:
        role = msg.get("role", "user")
        raw_content = msg.get("content", [])
        content = []
        if isinstance(raw_content, str):
            raw_content = [{"type": "input_text", "text": raw_content}]
        for b in raw_content:
            block_type = b.get("type", "text")
            # Auto-fix legacy
            if block_type == "text":
                block_type = "input_text"
            
            if block_type == "input_text":
                content.append({"type": "input_text", "text": b.get("text", "")})
            else:
                content.append(b)
        
        out.append({"role": role, "content": content})
    return out

async def ask_gpt5(
    input_blocks: list[dict[str, Any]],
    *,
    model: str = OPENAI_MODEL,
    max_output_tokens: int = 1200,
) -> str:
    """
    Call Responses API with proper async.
    
    Note: Responses API does NOT support temperature, top_p, response_format, etc.
    Only model, input, and max_output_tokens are supported.
    
    Args:
        input_blocks: List with role/content (blocks auto-normalized to input_text)
        model: gpt-5, gpt-5-mini, etc.
        max_output_tokens: Max tokens in response
        
    Returns:
        Response text
        
    Raises:
        HTTPException with 400/429/502/504 and detail message
    """
    client = get_async_client()
    
    # Normalize input
    normalized = _normalize_input(input_blocks)
    
    # Calculate input size for metrics
    input_chars = sum(
        len(b.get("text", ""))
        for msg in normalized
        for b in msg.get("content", [])
        if b.get("type") == "input_text"
    )
    
    # Build payload - ONLY supported parameters for Responses API
    payload: Dict[str, Any] = {
        "model": model,
        "input": normalized,
        "max_output_tokens": max_output_tokens,
    }
    
    # Timing metrics
    t_start = time.time()
    retry_count = 0
    
    try:
        roles = [m.get("role", "user") for m in normalized]
        log.info(
            "[GPT5] Calling model=%s (max_output_tokens=%d, input_chars=%d, messages=%d, roles=%s)",
            model,
            max_output_tokens,
            input_chars,
            len(normalized),
            ",".join(roles),
        )
        
        # Direct await - no run_in_executor!
        resp = await client.responses.create(**payload)
        
        t_end = time.time()
        duration = t_end - t_start
        
        # Extract text from GPT-5 response
        # Response structure: output = [reasoning_item, message_item]
        # message_item.content[0].text contains the final answer
        output_text = ""
        if resp.output:
            for item in resp.output:
                # Look for message items (type='message')
                item_dict = item if isinstance(item, dict) else (item.model_dump() if hasattr(item, 'model_dump') else {})
                item_type = item_dict.get('type')
                
                if item_type == 'message':
                    content = item_dict.get('content', [])
                    if content and len(content) > 0:
                        # content[0] should have 'text' field
                        text_block = content[0]
                        if isinstance(text_block, dict) and 'text' in text_block:
                            output_text = text_block['text']
                            break
        
        # Fallback to output_text if available (for compatibility)
        if not output_text and hasattr(resp, 'output_text') and resp.output_text:
            output_text = resp.output_text
        
        if not output_text:
            # Try to handle incomplete responses gracefully
            if resp.status == 'incomplete':
                log.warning("[GPT5] Response incomplete (status: %s) - may need more max_output_tokens or request simplification", resp.status)
                # Try to extract partial output if available
                if resp.output:
                    for item in resp.output:
                        item_dict = item if isinstance(item, dict) else (item.model_dump() if hasattr(item, 'model_dump') else {})
                        # Check for any text content
                        content = item_dict.get('content', [])
                        if content:
                            for text_block in content:
                                if isinstance(text_block, dict) and text_block.get('text'):
                                    partial_text = text_block['text']
                                    log.info("[GPT5] Extracted partial text from incomplete response (%d chars)", len(partial_text))
                                    return partial_text
                # No partial text found
                raise HTTPException(
                    status_code=504,
                    detail=f"GPT-5 response incomplete - try reducing request complexity or increasing max_output_tokens (current: {max_output_tokens})"
                )
            else:
                log.error("[GPT5] Could not extract text from response! Status: %s", resp.status)
                raise ValueError(f"Response status: {resp.status}, no text extracted")
        
        output_chars = len(output_text)
        
        log.info(
            "[GPT5] Success in %.2fs (output_chars=%d, retries=%d)",
            duration,
            output_chars,
            retry_count
        )
        
        return output_text
        
    except BadRequestError as e:
        # 400: Bad input (type:'text', invalid params, temperature with response_format, etc.)
        t_end = time.time()
        log.error(
            "[GPT5] BadRequestError after %.2fs: %s",
            t_end - t_start,
            str(e)
        )
        raise HTTPException(
            status_code=400,
            detail=f"GPT-5 validation error: {str(e)}"
        )
    
    except RateLimitError as e:
        t_end = time.time()
        log.error(
            "[GPT5] RateLimitError after %.2fs: %s",
            t_end - t_start,
            str(e)
        )
        raise HTTPException(
            status_code=429,
            detail="OpenRouter rate limit exceeded. Please retry in a moment."
        )
    
    except APITimeoutError as e:
        t_end = time.time()
        log.error(
            "[GPT5] APITimeoutError after %.2fs: %s",
            t_end - t_start,
            str(e)
        )
        raise HTTPException(
            status_code=504,
            detail=f"OpenRouter request timeout after {t_end - t_start:.1f}s: {str(e)}"
        )
    
    except APIConnectionError as e:
        t_end = time.time()
        log.error(
            "[GPT5] APIConnectionError after %.2fs: %s",
            t_end - t_start,
            str(e)
        )
        raise HTTPException(
            status_code=502,
            detail=f"Cannot connect to OpenRouter: {str(e)}"
        )
    
    except APIError as e:
        t_end = time.time()
        log.error(
            "[GPT5] APIError after %.2fs: %s",
            t_end - t_start,
            str(e)
        )
        raise HTTPException(
            status_code=502,
            detail=f"OpenRouter upstream error: {str(e)}"
        )
    
    except Exception as e:
        t_end = time.time()
        log.exception(
            "[GPT5] Unexpected error after %.2fs",
            t_end - t_start
        )
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )
