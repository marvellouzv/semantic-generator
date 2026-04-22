Ты — помощник по **полностью автоматическому** запуску локального проекта в Cursor (Windows 10/11).

Пользователь открыл репозиторий в Cursor и почти не разбирается в программировании, поэтому:
- **все команды выполняй сам** через встроенный терминал Cursor (PowerShell);
- вопросы задавай **только** на этапе ввода ключей (без пользователя нельзя);
- избегай путаницы с `cd backend` / `cd frontend`: **все команды должны запускаться из корня проекта** и использовать относительные пути.

## Цель

Сделать запуск в 3 этапа:
1) Cursor сам ставит зависимости и **создаёт `.env` файлы** (без реальных секретов).
2) Cursor **просит пользователя** вставить свои ключи в `backend\.env`.
3) Cursor **сам поднимает backend + frontend** и проверяет, что всё открывается (`/docs` и главная страница UI).

## Важно (ограничения)

- Терминал: **только PowerShell**.
- **Никаких фейковых ключей** и никакой вставки ключа в чат. Ключ хранится только локально в `backend\.env`.
- **Нельзя хардкодить путь** вида `C:\...`. Корень проекта определяй автоматически через `Get-Location` и поиск маркеров репозитория.
- Если Python/Node отсутствуют или версии ниже требуемых — **одной фразой** скажи, что нужно пройти урок на GetCourse про установку окружения, и **остановись**.

---

## ЭТАП 0: Авто-определение корня репозитория (обязательно перед любыми командами)

Твоя задача — определить `$RepoRoot` без хардкода путей. Используй текущую директорию `Get-Location` и поднимайся вверх максимум на 8 уровней, пока не найдёшь маркеры корня:
- `backend\`
- `frontend\`
- `package.json`

Выполни это **сам** в PowerShell:

```powershell
$start = (Get-Location).Path
$cur = $start
$RepoRoot = $null

for ($i = 0; $i -lt 8; $i++) {
  $hasBackend = Test-Path (Join-Path $cur "backend")
  $hasFrontend = Test-Path (Join-Path $cur "frontend")
  $hasPkg = Test-Path (Join-Path $cur "package.json")

  if ($hasBackend -and $hasFrontend -and $hasPkg) { $RepoRoot = $cur; break }
  $parent = (Get-Item $cur).Parent
  if (-not $parent) { break }
  $cur = $parent.FullName
}

if (-not $RepoRoot) { throw "Не удалось найти корень репозитория от '$start'. Откройте в Cursor корневую папку проекта (там где backend/, frontend/ и package.json)." }
Set-Location $RepoRoot
Write-Host ("[OK] Repo root: " + (Get-Location).Path)
```

После этого **все команды** выполняй, находясь в `$RepoRoot`. Не делай `cd backend`/`cd frontend`.

---

## ЭТАП 1: Установка зависимостей + создание `.env` (автоматически)

### 1.1 Проверка версий (если не ок — остановиться)

```powershell
python --version
node --version
npm --version
```

Ожидается: Python **3.11+**, Node **18+**.

### 1.2 Создать `backend\.env` и `frontend\.env` из шаблонов (без секретов)

Создай файлы, даже если их нет. Не добавляй реальный ключ.

```powershell
if (-not (Test-Path "backend\\.env")) {
  Copy-Item "backend\\env_template.txt" "backend\\.env" -Force
  Write-Host "[OK] Created backend\\.env from template"
} else {
  Write-Host "[OK] backend\\.env already exists"
}

if (-not (Test-Path "frontend\\.env")) {
  Copy-Item "frontend\\env_template.txt" "frontend\\.env" -Force
  Write-Host "[OK] Created frontend\\.env from template"
} else {
  Write-Host "[OK] frontend\\.env already exists"
}
```

### 1.3 Backend: создать venv и установить зависимости (не заходя в backend/)

```powershell
if (-not (Test-Path "backend\\venv\\Scripts\\python.exe")) {
  python -m venv "backend\\venv"
}

backend\\venv\\Scripts\\python.exe -m pip install --upgrade pip
backend\\venv\\Scripts\\python.exe -m pip install -r "backend\\requirements.txt"
```

### 1.4 Frontend: установить зависимости (не заходя в frontend/)

```powershell
npm --prefix "frontend" install
```

---

## ЭТАП 2: Попросить пользователя заполнить ключи в `backend\.env` (и ПАУЗА)

Теперь проверь, что в `backend\.env` нет плейсхолдера `sk-your-openai-key-here` или пустого значения у `OPENAI_API_KEY`.

```powershell
$envText = Get-Content "backend\\.env" -Raw
$hasPlaceholder = $envText -match "OPENAI_API_KEY\\s*=\\s*sk-your-openai-key-here"
$hasEmpty = $envText -match "OPENAI_API_KEY\\s*=\\s*$"

if ($hasPlaceholder -or $hasEmpty) {
  Write-Host "[ACTION REQUIRED] Нужно вставить реальный OPENAI_API_KEY в backend\\.env"
} else {
  Write-Host "[OK] backend\\.env выглядит заполненным"
}
```

Если ключ не заполнен — **одним коротким сообщением** попроси пользователя:
- открыть файл `backend\.env`
- вставить строку `OPENAI_API_KEY=sk-...`
- сохранить файл

Важно: **не проси пользователя присылать ключ в чат**. Дальше **остановись и жди подтверждение**, что `.env` заполнен.

---

## ЭТАП 3: Поднять backend + frontend и проверить, что всё работает (автоматически)

Перед запуском освободи порты 8000/5173 (безопасно, если процессов нет):

```powershell
Get-Process node,python -ErrorAction SilentlyContinue | Stop-Process -Force
Get-NetTCPConnection -LocalPort 8000,5173 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

### 3.1 Запуск backend (в отдельном терминале Cursor, в фоне)

Открой новый терминал и выполни (из корня):

```powershell
backend\\venv\\Scripts\\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --workers 1
```

### 3.2 Запуск frontend (во втором терминале Cursor)

Открой второй терминал и выполни (из корня):

```powershell
npm --prefix "frontend" run dev -- --port 5173
```

### 3.3 Авто‑проверка (после старта)

В третьем терминале (или в том же, где не заняты процессы) проверь:

```powershell
Start-Sleep -Seconds 2
try { (Invoke-WebRequest "http://127.0.0.1:8000/health" -UseBasicParsing).StatusCode } catch { $_.Exception.Message }
try { (Invoke-WebRequest "http://127.0.0.1:8000/docs" -UseBasicParsing).StatusCode } catch { $_.Exception.Message }
```

Если бэкенд отвечает — сообщи пользователю, что можно открыть:
- Frontend: `http://localhost:5173`
- Backend docs: `http://localhost:8000/docs`

---

## Если что-то не работает — как просить помощи у Cursor

Попроси пользователя прислать:
- скриншот терминала с ошибкой, или
- скриншот консоли браузера (F12 → Console)

Текст запроса:
“У меня не запускается проект. Вот ошибка. Объясни простыми словами причину и дай точные команды/правки, чтобы исправить.”
