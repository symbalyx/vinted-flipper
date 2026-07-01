# JARVIS v5.6 — Lancement PRODUCTION Windows (Waitress).
# Usage :  powershell -ExecutionPolicy Bypass -File scripts\run_windows.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

# ── Environnement (.env) ──
if (Test-Path ".env") {
  Get-Content ".env" | ForEach-Object {
    if ($_ -match '^\s*([^#=]+)=(.*)$') {
      [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim())
    }
  }
}
$Host_ = if ($env:JARVIS_HOST) { $env:JARVIS_HOST } else { "0.0.0.0" }
$Port  = if ($env:JARVIS_PORT) { $env:JARVIS_PORT } else { "8004" }

# ── Venv ──
if (-Not (Test-Path ".venv")) {
  python -m venv .venv
  & .\.venv\Scripts\python.exe -m pip install -U pip
  & .\.venv\Scripts\python.exe -m pip install -r requirements_v4.txt
  & .\.venv\Scripts\python.exe -m pip install waitress
}

New-Item -ItemType Directory -Force -Path "logs" | Out-Null
Write-Host "JARVIS (Waitress) -> http://$($Host_):$($Port)  (healthcheck: /api/health)"

# Waitress ne gère pas TLS : placer IIS / un reverse-proxy HTTPS devant en prod.
Set-Location "server"
& ..\.venv\Scripts\waitress-serve.exe --listen="$($Host_):$($Port)" --threads=8 wsgi:app
