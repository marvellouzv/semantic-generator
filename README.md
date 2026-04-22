## Semantic Generator

Сервис для генерации русской SEO-семантики в виде кластеров с UI для фильтрации, шаблонов, истории и экспорта.

### Что умеет

- Этап 1 (`Setup -> Clusters`): генерация head-кластеров по теме и интентам.
- Этап 2 (`Expansion`): расширение запросов по parent themes с доп. требованиями.
- Шаблоны: сохранение, загрузка, дополнение шаблона новыми кластерами.
- Экспорт: `XLSX` / `CSV`.
- Метрики: запросы, время ответа, токены, стоимость.

### Архитектура

- Backend: FastAPI ([backend/app/main.py](C:\Project\semantic-generator\backend\app\main.py))
- Frontend: Vite + React
- LLM: OpenAI-compatible API (`AsyncOpenAI.responses.create`) через провайдер OpenRouter

### Требования

- Windows 10/11
- Python 3.11+
- Node.js 18+
- Валидный API ключ OpenRouter

Документация:
- [OpenRouter API Reference](https://openrouter.ai/docs/api-reference/overview)

### Переменные окружения

Создайте `backend/.env` по шаблону [backend/env_template.txt](C:\Project\semantic-generator\backend\env_template.txt):

```env
OPENAI_API_KEY=sk-or-v1-...
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=openai/gpt-5.1
OPENAI_FALLBACK_MODEL=openai/gpt-5-mini
REQUEST_TIMEOUT_SECONDS=300
USE_GPT5_ENSEMBLE=true
REDIS_URL=redis://localhost:6379
```

Опциональные заголовки OpenRouter:

```env
OPENROUTER_SITE_URL=https://your-site.example
OPENROUTER_SITE_NAME=Semantic Generator
```

Примечание: legacy-переменные `OPENROUTER_*` поддерживаются как fallback, но основной контракт проекта — `OPENAI_*`.

### Быстрый запуск

```powershell
npm install
npm run setup
npm run dev
```

Или вручную:

- Backend: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1`
- Frontend: `npm run dev -- --port 5173`

### Проверка

- Backend health: `http://localhost:8000/health`
- LLM health: `http://localhost:8000/api/health/llm`
- Frontend: `http://localhost:5173`

### Полезные API эндпоинты

- `POST /api/v1/upper-graph`
- `POST /api/v1/expand-queries`
- `POST /api/v1/export`
- `POST /api/v1/export-clusters`
- `GET /api/v1/templates`
- `GET /api/v1/stats`

### Troubleshooting

- `401/403`:
1. Проверить `OPENAI_API_KEY`
2. Проверить `OPENAI_BASE_URL`
3. Проверить `OPENAI_MODEL`

- Ошибка `invalid_api_key`:
1. Проверить, что ключ создан именно в OpenRouter
2. Пересоздать ключ и заменить в `backend/.env`

### Актуальность документации

Обязательные файлы:

- [README.md](C:\Project\semantic-generator\README.md)
- [arent.md](C:\Project\semantic-generator\arent.md)
- [handoff.md](C:\Project\semantic-generator\handoff.md)

### UI Theme

- Swiss Minimal is applied in frontend (Inter typography, clean grid, neutral surfaces, restrained shadows, high-contrast controls).

### GitHub Integration (Safe Setup)

Before first push, make sure secrets are not tracked:
- `.env` and any `.env.*` files are ignored by `.gitignore`.
- Use `backend/env_template.txt` as a template and keep real keys only in local `backend/.env`.

Recommended initial steps:
1. `git init`
2. `git add .`
3. `git commit -m "Initial import: semantic-generator"`
4. `git branch -M main`
5. `git remote add origin git@github.com:marvellouzv/semantic-generator.git`
6. `git push -u origin main`

If remote already has history, run:
- `git pull --rebase origin main` then resolve conflicts and push.
