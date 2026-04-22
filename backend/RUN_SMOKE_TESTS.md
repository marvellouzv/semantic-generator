# Smoke Tests для GPT-5 Integration

## Быстрый запуск

### 1. Установка переменных окружения
```powershell
# Windows PowerShell
cd backend
$env:OPENAI_API_KEY="sk-your-key-here"
```

### 2. Запуск тестов
```powershell
python test_gpt5_smoke.py
```

### Ожидаемый результат
```
============================================================
GPT-5 Responses API Smoke Test Suite
============================================================

=== Test 1: Client Sanity Check ===
✅ PASS: AsyncOpenAI.responses.create exists and is async

=== Test 2: Short Request (< 5s) ===
[GPT5] Calling gpt-5 (max_output_tokens=64, input_chars=27, response_format=text, temperature=0.2)
[GPT5] Success in 2.34s (output_chars=15, retries=0)
✅ PASS: Request completed in 2.34s
   Response: OK

=== Test 3: JSON Mode (Temperature Guard) ===
[GPT5] Calling gpt-5 (max_output_tokens=128, input_chars=26, response_format=JSON, temperature=N/A)
[GPT5] Success in 3.12s (output_chars=18, retries=0)
✅ PASS: JSON mode works, temperature was ignored
   Response: {"status": "ok"}

=== Test 4: Forbidden Patterns Check ===
✅ PASS: No forbidden patterns found

=== Test 5: Error Mapping ===
✅ PASS: HTTPException raised with status 400

============================================================
SUMMARY
============================================================
Passed: 5/5
✅ ALL TESTS PASSED
```

---

## Troubleshooting

### ❌ Test 1 Failed: "AsyncOpenAI.responses not found"
**Причина**: Устаревшая версия openai SDK

**Решение**:
```bash
pip install --upgrade openai>=1.60.0
```

### ❌ Test 2 Failed: Timeout or API Error
**Причина**: Неверный API ключ или проблемы с сетью

**Решение**:
```bash
# Проверьте API ключ
echo $env:OPENAI_API_KEY  # PowerShell
echo $OPENAI_API_KEY      # Linux/Mac

# Проверьте доступ к OpenAI
curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"
```

### ❌ Test 4 Failed: Forbidden patterns found
**Причина**: В коде остались запрещённые паттерны

**Решение**:
```bash
# Проверьте каждый файл из ошибки
grep -n "chat.completions" backend/app/filename.py
grep -n "max_tokens" backend/app/filename.py

# Исправьте найденные паттерны согласно .cursorrules
```

### ⚠️ Warning: Request took > 5s
**Это нормально** для первого запроса (cold start).

Повторите тест - следующие запросы должны быть быстрее.

---

## Дополнительные проверки

### 1. Проверка запрещённых паттернов вручную
```bash
cd backend

# Должно быть пусто (или только комментарии)
grep -r "chat\.completions" app/
grep -r "max_tokens" app/  # кроме max_output_tokens
grep -r "run_until_complete" app/  # кроме комментариев
```

### 2. Тест длинной генерации (опционально)
```python
# backend/test_batch_manual.py
import asyncio
from app.batch_generator import generate_large_query_set

async def test():
    queries = await generate_large_query_set(
        topic="холодильники",
        intents=["commercial", "informational"],
        target_count=500
    )
    print(f"Generated {len(queries)} unique queries")
    print("Sample:", queries[:5])

asyncio.run(test())
```

Ожидаемое время: < 2 минуты для 500 запросов

---

## Continuous Integration

### Pre-commit Hook (рекомендуется)
```bash
# .git/hooks/pre-commit
#!/bin/bash
cd backend
python test_gpt5_smoke.py || exit 1
```

### GitHub Actions (пример)
```yaml
# .github/workflows/test.yml
name: GPT-5 Smoke Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -r backend/requirements.txt
      - run: cd backend && python test_gpt5_smoke.py
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

---

## Контакты и поддержка

- Чеклист миграции: `GPT5_MIGRATION_CHECKLIST.md`
- Правила проекта: `.cursorrules`
- Основной README: `README.md`

При возникновении проблем проверьте логи:
```bash
# Windows
Get-Content logs\backend.log -Tail 50

# Linux/Mac
tail -f logs/backend.log
```




