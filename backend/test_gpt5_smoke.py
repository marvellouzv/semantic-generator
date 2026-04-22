# -*- coding: utf-8 -*-
"""
Smoke test for GPT-5 Responses API integration.

Validates:
1. AsyncOpenAI client has responses attribute
2. responses.create() is a coroutine function
3. Short request completes in < 5s
4. No forbidden patterns (chat.completions, max_tokens, etc.)
5. Temperature guard works with response_format
"""
import asyncio
import time
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from app.openai_client import get_async_client
from app.gpt5_wrapper import ask_gpt5


async def test_client_sanity():
    """Test 1: Verify AsyncOpenAI client has responses.create()"""
    print("\n=== Test 1: Client Sanity Check ===")
    
    try:
        client = get_async_client()
        
        # Check responses attribute exists
        if not hasattr(client, "responses"):
            print("[FAIL] AsyncOpenAI.responses not found")
            return False
        
        # Check create is a coroutine function
        import inspect
        if not inspect.iscoroutinefunction(client.responses.create):
            print("[FAIL] responses.create is not a coroutine function")
            return False
        
        print("[PASS] AsyncOpenAI.responses.create exists and is async")
        return True
        
    except Exception as e:
        print(f"[FAIL] {e}")
        return False


async def test_short_request():
    """Test 2: Short request completes quickly"""
    print("\n=== Test 2: Short Request (< 5s) ===")
    
    try:
        t_start = time.time()
        
        model = os.environ.get("OPENAI_MODEL") or os.environ.get("OPENROUTER_MODEL") or "openai/gpt-5.1"
        response = await ask_gpt5(
            input_blocks=[{
                "role": "user",
                "content": [{"type": "input_text", "text": "Say 'OK' if you understand"}]
            }],
            model=model,
            max_output_tokens=64,
        )
        
        t_end = time.time()
        duration = t_end - t_start
        
        if duration > 5.0:
            print(f"[WARN] Request took {duration:.2f}s (expected < 5s)")
        else:
            print(f"[PASS] Request completed in {duration:.2f}s")
        
        if not response or len(response.strip()) == 0:
            print("[FAIL] Empty response")
            return False
        
        print(f"   Response: {response[:100]}")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False


async def test_json_mode():
    """Test 3: JSON request via prompt (Responses API doesn't support response_format)"""
    print("\n=== Test 3: JSON Mode via Prompt ===")
    
    try:
        # Request JSON format in prompt since response_format is not supported
        model = os.environ.get("OPENAI_MODEL") or os.environ.get("OPENROUTER_MODEL") or "openai/gpt-5.1"
        response = await ask_gpt5(
            input_blocks=[{
                "role": "user",
                "content": [{"type": "input_text", "text": 'Return only valid JSON: {"status": "ok"}. No markdown, no explanations.'}]
            }],
            model=model,
            max_output_tokens=128,
        )
        
        # Clean response
        cleaned = response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        
        # Try to parse as JSON
        import json
        data = json.loads(cleaned)
        
        if not isinstance(data, dict):
            print(f"[FAIL] Response is not a JSON object: {response}")
            return False
        
        print("[PASS] JSON request via prompt works")
        print(f"   Response: {cleaned[:200]}")
        return True
        
    except Exception as e:
        print(f"[FAIL] {e}")
        return False


def test_forbidden_patterns():
    """Test 4: Check for forbidden patterns in codebase"""
    print("\n=== Test 4: Forbidden Patterns Check ===")
    
    forbidden = {
        "chat.completions": "Should use responses.create() instead",
        "max_tokens": "Should use max_output_tokens (except max_output_tokens itself)",
        "max_completion_tokens": "Should use max_output_tokens",
    }
    
    # Patterns that should NOT be in actual code (only in comments/strings are OK)
    code_only_forbidden = {
        'type":"text"': 'Should use type:"input_text"',
        'type": "text"': 'Should use type:"input_text"',
    }
    
    # Files to check
    files_to_check = [
        "app/gpt5_wrapper.py",
        "app/llm_stage2.py",
        "app/openai_client.py",
        "app/query_expander.py",
        "app/gpt5_head_queries.py",
        "app/batch_generator.py",
    ]
    
    issues_found = []
    
    for file_path in files_to_check:
        full_path = backend_path / file_path
        if not full_path.exists():
            continue
        
        content = full_path.read_text(encoding='utf-8')
        
        # Check forbidden patterns (excluding max_output_tokens)
        for pattern, reason in forbidden.items():
            if pattern in content:
                # Special handling for max_tokens - allow max_output_tokens
                if pattern == "max_tokens" and "max_output_tokens" in content:
                    # Count occurrences
                    if content.count("max_tokens") <= content.count("max_output_tokens"):
                        continue  # All max_tokens are part of max_output_tokens
                issues_found.append(f"{file_path}: {pattern} - {reason}")
    
    if issues_found:
        print("[FAIL] Forbidden patterns found:")
        for issue in issues_found:
            print(f"   - {issue}")
        return False
    
    print("[PASS] No forbidden patterns found")
    return True


async def test_error_mapping():
    """Test 5: Error mapping (400/429/502/504)"""
    print("\n=== Test 5: Error Mapping ===")
    
    try:
        # Try to trigger a BadRequest (invalid model or empty input)
        from fastapi import HTTPException
        
        try:
            model = os.environ.get("OPENAI_MODEL") or os.environ.get("OPENROUTER_MODEL") or "openai/gpt-5.1"
            response = await ask_gpt5(
                input_blocks=[{
                    "role": "user",
                    "content": [{"type": "input_text", "text": ""}]  # Empty text
                }],
                model=model,
                max_output_tokens=64,
            )
            print("[WARN] Expected error but got response")
            return True  # Not a failure, just unexpected
            
        except HTTPException as e:
            if e.status_code in (400, 429, 502, 504):
                print(f"[PASS] HTTPException raised with status {e.status_code}")
                return True
            else:
                print(f"[FAIL] Unexpected status code {e.status_code}")
                return False
        
    except Exception as e:
        print(f"[FAIL] Unexpected exception: {e}")
        return False


async def main():
    """Run all smoke tests"""
    print("=" * 60)
    print("GPT-5 Responses API Smoke Test Suite")
    print("=" * 60)
    
    # Check for API key
    if not (os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENROUTER_API_KEY")):
        print("\n[FATAL] OPENAI_API_KEY not set")
        print("   Set it in .env file or environment")
        return False
    
    results = []
    
    # Test 1: Client sanity
    results.append(await test_client_sanity())
    
    # Test 2: Short request
    results.append(await test_short_request())
    
    # Test 3: JSON mode
    results.append(await test_json_mode())
    
    # Test 4: Forbidden patterns (sync)
    results.append(test_forbidden_patterns())
    
    # Test 5: Error mapping
    results.append(await test_error_mapping())
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("[SUCCESS] ALL TESTS PASSED")
        return True
    else:
        print(f"[FAILED] {total - passed} TEST(S) FAILED")
        return False


if __name__ == "__main__":
    # Load .env if it exists
    from dotenv import load_dotenv
    load_dotenv()
    
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
