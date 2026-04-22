# HANDOFF.md

## История изменений

### 2026-04-22 — Документационный контур

- Создан `arent.md` с правилами работы.
- Создан `handoff.md` как журнал изменений.
- В `README.md` добавлен раздел о поддержании актуальности документов.

Затронутые файлы:
- `README.md`
- `arent.md`
- `handoff.md`

### 2026-04-22 — Миграция LLM на ru-openrouter

- Backend переведен на `ru-openrouter` как основной провайдер LLM.
- Добавлена поддержка переменных `OPENROUTER_*` с fallback на `OPENAI_*`.
- Базовый URL по умолчанию изменен на `https://api.ru-openrouter.ru/v1`.
- Модель переведена на provider-prefixed формат (`openai/gpt-5`, fallback `openai/gpt-5-mini`).
- Убраны жесткие проверки формата модели `gpt-5*`, чтобы корректно работать с OpenRouter model IDs.
- Обновлены сообщения об ошибках и health/статусы под OpenRouter.
- Полностью актуализированы `README.md` и `backend/env_template.txt` под новый провайдер.
- В `arent.md` добавлен отдельный регламент по LLM-интеграции.

Затронутые файлы:
- `backend/app/openai_client.py`
- `backend/app/gpt5_wrapper.py`
- `backend/app/main.py`
- `backend/app/gpt5_head_queries.py`
- `backend/app/llm_stage2.py`
- `backend/app/query_expander.py`
- `backend/env_template.txt`
- `README.md`
- `arent.md`
- `handoff.md`

Что проверить после изменений:
- Наличие `OPENROUTER_API_KEY` в `backend/.env`.
- Корректность `OPENROUTER_MODEL`/`OPENROUTER_FALLBACK_MODEL`.
- Успешный запуск `npm run dev`.
- Проверка `GET /health` и `GET /api/health/llm`.
- Проверка генерации через `POST /api/v1/upper-graph`.

Риски/заметки:
- Старые smoke-тесты и вспомогательные скрипты с названием `openai`/`gpt5` частично остались и могут требовать отдельной чистки нейминга.
- Поле `total_openai_cost` в статистике сохранено для обратной совместимости API, добавлено новое поле `total_llm_cost`.

### 2026-04-22 — Нормализация env-контракта на OPENAI_*

- Контракт конфигурации переведен на `OPENAI_*` как основной:
  - `OPENAI_API_KEY`
  - `OPENAI_BASE_URL`
  - `OPENAI_MODEL`
  - `OPENAI_FALLBACK_MODEL`
- Поддержка `OPENROUTER_*` оставлена только как fallback для обратной совместимости.
- По умолчанию base URL установлен в `https://openrouter.ai/api/v1`.
- По умолчанию модель установлена в `openai/gpt-5.1`.
- В клиент добавлены optional заголовки `HTTP-Referer` и `X-Title` через env.
- Документация и шаблон env синхронизированы с новым контрактом.

Затронутые файлы:
- `backend/app/openai_client.py`
- `backend/app/gpt5_wrapper.py`
- `backend/app/main.py`
- `backend/app/gpt5_head_queries.py`
- `backend/app/llm_stage2.py`
- `backend/app/query_expander.py`
- `backend/test_gpt5_smoke.py`
- `backend/env_template.txt`
- `README.md`
- `arent.md`
- `handoff.md`

### 2026-04-22 — Исправление `Invalid URL` при генерации

- Исправлен frontend API base URL resolver в `frontend/src/api.ts`.
- Добавлена безопасная нормализация `VITE_API_URL`:
  - автодобавление `http://`, если протокол не указан
  - fallback на `http://localhost:8000`, если значение невалидно
- Устранена ошибка браузера `Failed to construct 'URL': Invalid URL` при нажатии "Сгенерировать" для некорректного `VITE_API_URL`.

Затронутые файлы:
- `frontend/src/api.ts`
- `handoff.md`

### 2026-04-22 - Swiss Minimal UI refresh

- Applied Swiss Minimal visual direction in frontend (Inter font, refined color tokens, cleaner surfaces, less aggressive shadows, compact top navigation).
- Updated base design tokens and global interaction styles for consistent controls/focus states.
- Refined key screens (App, SetupScreen, UpperReviewScreen) to match the new visual system.
- Updated README with current UI theme status.

Touched files:
- frontend/src/App.css
- frontend/tailwind.config.js
- frontend/src/App.tsx
- frontend/src/components/SetupScreen.tsx
- frontend/src/components/UpperReviewScreen.tsx
- README.md
- handoff.md

### 2026-04-22 - Swiss Minimal polish pass 2

- Unified visual accents across modals, action bars, and secondary CTA buttons.
- Replaced remaining purple/green emphasis in key user flows with Swiss Minimal palette (blue/slate/amber).
- Updated modal overlays to softer backdrop blur and cleaner container borders.
- Verified production frontend build after styling changes.

Touched files:
- frontend/src/components/SetupScreen.tsx
- frontend/src/components/UpperReviewScreen.tsx
- frontend/src/components/TemplateManager.tsx
- frontend/src/components/HistoryPanel.tsx
- frontend/src/components/MobileClusterCard.tsx
- frontend/src/components/ClusterDashboard.tsx
- frontend/src/components/BatchProcessing.tsx
- handoff.md

### 2026-04-22 - Swiss Minimal pixel pass (filters/export)

- Finalized Swiss Minimal styling for filter and export dialogs.
- EnhancedFilters: updated container/header/presets/inputs/checklists to slate-blue tokens and cleaner contrast.
- ExportDialog: unified modal shell, selection cards, quick templates, advanced options, and footer action row with the same token system.
- Verified frontend production build after changes.

Touched files:
- frontend/src/components/EnhancedFilters.tsx
- frontend/src/components/ExportDialog.tsx
- handoff.md

### 2026-04-22 - GitHub binding and first push

- Initialized local git repository in project root.
- Hardened .gitignore for secrets: ignored .env/.env.*, ackend/.env, backups, and local DB file.
- Added README section with safe GitHub onboarding steps and secret handling guidance.
- Created initial commit and pushed main to git@github.com:marvellouzv/semantic-generator.git.

Touched files:
- .gitignore
- README.md
- handoff.md
