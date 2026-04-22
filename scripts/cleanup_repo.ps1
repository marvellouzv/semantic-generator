Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Stop-ListenerOnPort {
  param(
    [Parameter(Mandatory = $true)][int]$Port
  )

  $conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  if (-not $conns) {
    Write-Host "No LISTEN on port $Port"
    return
  }

  $procIds = $conns | Select-Object -ExpandProperty OwningProcess -Unique
  foreach ($procId in $procIds) {
    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
    $name = if ($proc) { $proc.ProcessName } else { "unknown" }
    Write-Host "Stopping PID $procId ($name) on port $Port"
    Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
  }
}

function Remove-PathForce {
  param(
    [Parameter(Mandatory = $true)][string]$RelativePath
  )

  $full = Join-Path (Get-Location) $RelativePath
  if (-not (Test-Path $full)) {
    return
  }

  Write-Host "Deleting $RelativePath"
  $item = Get-Item $full -Force
  if ($item.PSIsContainer) {
    cmd /c "rmdir /s /q `"$full`"" | Out-Null
  } else {
    cmd /c "del /f /q `"$full`"" | Out-Null
  }
}

Write-Host "== Stop dev servers (ports 8000, 5173) =="
Stop-ListenerOnPort -Port 8000
Stop-ListenerOnPort -Port 5173
Start-Sleep -Seconds 1

Write-Host "== Remove installed deps & build artifacts (keeps backend/.env and templates/) =="
$deleteList = @(
  ".venv",
  "backend\\venv",
  "backend\\metrics.db",
  "frontend\\node_modules",
  "frontend\\dist",
  "frontend\\.vite",
  "node_modules",
  "dist",
  "logs"
)

foreach ($p in $deleteList) {
  Remove-PathForce -RelativePath $p
}

Write-Host "== Remove caches (safe to delete) =="
Get-ChildItem -Path . -Directory -Recurse -Force -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -in @("__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".parcel-cache", ".vite") } |
  ForEach-Object { cmd /c "rmdir /s /q `"$($_.FullName)`"" | Out-Null }

Write-Host "Done."


