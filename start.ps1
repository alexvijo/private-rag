#!/usr/bin/env pwsh
<#
Levanta el backend (FastAPI) y el frontend (Angular) en paralelo para desarrollo local,
sin Docker. Crea el entorno virtual e instala dependencias si hace falta.

Uso:
  ./start.ps1              # backend + frontend
  ./start.ps1 -SkipInstall # omite pip install / npm install (arranque rápido)
#>
param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$backendDir = Join-Path $root "backend"
$frontendDir = Join-Path $root "frontend"

function Write-Step($msg) {
    Write-Host ""
    Write-Host "==> $msg" -ForegroundColor Cyan
}

# --- Backend: venv + dependencias ---
Write-Step "Preparando backend"

$venvDir = Join-Path $backendDir "venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Creando entorno virtual en backend/venv ..."
    python -m venv $venvDir
}

if (-not $SkipInstall) {
    Write-Host "Instalando dependencias del backend (pip install -r requirements.txt) ..."
    & $venvPython -m pip install --quiet --upgrade pip
    & $venvPython -m pip install --quiet -r (Join-Path $backendDir "requirements.txt")
}

$envFile = Join-Path $backendDir ".env"
$envExample = Join-Path $backendDir ".env.example"
if (-not (Test-Path $envFile) -and (Test-Path $envExample)) {
    Copy-Item $envExample $envFile
    Write-Host "Creado backend/.env a partir de .env.example (ajusta LLM_PROVIDER si hace falta)."
}

# --- Frontend: node_modules ---
Write-Step "Preparando frontend"

if (-not $SkipInstall -and -not (Test-Path (Join-Path $frontendDir "node_modules"))) {
    Write-Host "Instalando dependencias del frontend (npm install) ..."
    Push-Location $frontendDir
    npm install
    Pop-Location
}

# --- Comprobación de Ollama (si es el proveedor configurado) ---
$llmProvider = "ollama"
if (Test-Path $envFile) {
    $match = Select-String -Path $envFile -Pattern "^LLM_PROVIDER=(.+)$" -ErrorAction SilentlyContinue
    if ($match) { $llmProvider = $match.Matches[0].Groups[1].Value.Trim() }
}

if ($llmProvider -eq "ollama") {
    Write-Step "Comprobando Ollama"
    try {
        Invoke-WebRequest -Uri "http://localhost:11434" -UseBasicParsing -TimeoutSec 2 | Out-Null
        Write-Host "Ollama responde en http://localhost:11434" -ForegroundColor Green
    } catch {
        Write-Host "Aviso: Ollama no responde en http://localhost:11434." -ForegroundColor Yellow
        Write-Host "Instala/arranca Ollama (https://ollama.com) y ejecuta 'ollama pull llama3.2'," -ForegroundColor Yellow
        Write-Host "o cambia LLM_PROVIDER=openai en backend/.env." -ForegroundColor Yellow
    }
}

# --- Lanzar backend y frontend en paralelo ---
# Se usa Start-Process (no Start-Job) porque Start-Job no propaga de forma fiable el
# stdout de un proceso nativo lanzado dentro del job, y Stop-Job no mata ese proceso
# hijo real (dejaría uvicorn/node huérfanos escuchando en el puerto tras Ctrl+C).
Write-Step "Arrancando backend (http://localhost:8000) y frontend (http://localhost:4200)"

$backendProc = Start-Process -FilePath $venvPython `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000" `
    -WorkingDirectory $backendDir -NoNewWindow -PassThru

# npm resuelve a npm.cmd en Windows: Start-Process no puede ejecutar un .cmd
# directamente como binario Win32, así que se lanza a través de cmd.exe /c.
$frontendProc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "npm", "start" `
    -WorkingDirectory $frontendDir -NoNewWindow -PassThru

Write-Host ""
Write-Host "Backend (PID $($backendProc.Id)) y frontend (PID $($frontendProc.Id)) arrancando." -ForegroundColor Green
Write-Host "Logs por debajo de este mensaje. Ctrl+C para detener ambos." -ForegroundColor Green
Write-Host ""

try {
    while (-not $backendProc.HasExited -and -not $frontendProc.HasExited) {
        Start-Sleep -Milliseconds 500
    }
    if ($backendProc.HasExited) {
        Write-Host "El backend ha terminado (código $($backendProc.ExitCode))." -ForegroundColor Red
    }
    if ($frontendProc.HasExited) {
        Write-Host "El frontend ha terminado (código $($frontendProc.ExitCode))." -ForegroundColor Red
    }
} finally {
    Write-Host ""
    Write-Host "Deteniendo backend y frontend..." -ForegroundColor Cyan
    if (-not $backendProc.HasExited) { Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue }
    if (-not $frontendProc.HasExited) { Stop-Process -Id $frontendProc.Id -Force -ErrorAction SilentlyContinue }
}
