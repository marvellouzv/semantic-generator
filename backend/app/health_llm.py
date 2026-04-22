# -*- coding: utf-8 -*-
"""
Health check for LLM service.
Smoke-test that responses.create() works at startup.
"""
from fastapi import APIRouter, HTTPException
from .gpt5_wrapper import ask_gpt5

router = APIRouter()

@router.get("/api/health/llm")
async def health_llm():
    """
    Smoke test: verify responses.create() works.
    Returns immediately if OK, or 5xx if broken.
    """
    try:
        response = await ask_gpt5(
            input_blocks=[{
                "role": "user",
                "content": [{"type": "input_text", "text": "Respond with: ok"}]
            }],
            max_output_tokens=128,
        )
        
        is_ok = "ok" in response.lower()
        return {
            "status": "ok" if is_ok else "warning",
            "sample": response[:64],
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"LLM unavailable: {str(e)}")
