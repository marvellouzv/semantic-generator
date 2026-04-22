#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Diagnostic: Verify OpenAI SDK has responses.create() and is async.
Run: python backend/diag_openai.py
Expected: has_responses=True, create_is_async=True
"""
import inspect
from openai import AsyncOpenAI, __version__

print("=" * 60)
print("[DIAGNOSIS] OpenAI SDK Compatibility Check")
print("=" * 60)

print(f"OpenAI version: {__version__}")

client = AsyncOpenAI(api_key="dummy")  # No real call needed for introspection

has_responses = hasattr(client, "responses")
print(f"has responses: {has_responses}")

if has_responses:
    is_coro = inspect.iscoroutinefunction(client.responses.create)
    print(f"create_is_async: {is_coro}")
    
    if is_coro:
        print("\n[OK] SUCCESS: responses.create() is async and ready")
    else:
        print("\n[ERROR] FAIL: responses.create() exists but is not async")
else:
    print("\n[ERROR] FAIL: AsyncOpenAI.responses not found")

print("=" * 60)
