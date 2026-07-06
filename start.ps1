#!/usr/bin/env pwsh
<#
Levanta Ollama + backend (FastAPI) + frontend (Angular) para desarrollo local.
Crea el entorno virtual e instala dependencias si hace falta, arranca Ollama si
no está corriendo, y comprueba que el modelo configurado esté descargado.

Uso:
  ./start.ps1              # Ollama + backend + frontend, cada uno en su ventana
  ./start.ps1 -SkipInstall # omite pip install / npm install (arranque rápido)
  ./start.ps1 -Docker      # delega en docker compose up --build (backend+frontend)
#>
param(
    [switch]$SkipInstall,
    [switch]$Docker
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$backendDir = Join-Path $root "backend"
$frontendDir = Join-Path $root "frontend"

function Write-Step($msg) {
    Write-Host ""
    Write-Host "==> $msg" -ForegroundColor Cyan
}

# --- Modo Docker: delega todo en docker compose ---
if ($Docker) {
    Write-Step "Arrancando con Docker Compose (backend + frontend)"
    Write-Host "Usa Ollama en el host vía host.docker.internal:11434 (ver docker-compose.yml)." -ForegroundColor Yellow

    $ollamaOk = $false
    try {
        Invoke-WebRequest -Uri "http://localhost:11434" -UseBasicParsing -TimeoutSec 2 | Out-Null
        $ollamaOk = $true
    } catch {}
    if (-not $ollamaOk) {
        Write-Step "Arrancando Ollama (no respondía en localhost:11434)"
        Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
        $deadline = (Get-Date).AddSeconds(20)
        while ((Get-Date) -lt $deadline) {
            try {
                Invoke-WebRequest -Uri "http://localhost:11434" -UseBasicParsing -TimeoutSec 2 | Out-Null
                Write-Host "Ollama responde en http://localhost:11434" -ForegroundColor Green
                break
            } catch { Start-Sleep -Milliseconds 500 }
        }
    } else {
        Write-Host "Ollama ya responde en http://localhost:11434" -ForegroundColor Green
    }

    Push-Location $root
    try {
        docker compose up --build
    } finally {
        Pop-Location
    }
    return
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

# --- Ollama: arrancar si hace falta + comprobar modelo configurado ---
$llmProvider = "ollama"
$ollamaModel = "llama3.2"
if (Test-Path $envFile) {
    $matchProvider = Select-String -Path $envFile -Pattern "^LLM_PROVIDER=(.+)$" -ErrorAction SilentlyContinue
    if ($matchProvider) { $llmProvider = $matchProvider.Matches[0].Groups[1].Value.Trim() }
    $matchModel = Select-String -Path $envFile -Pattern "^OLLAMA_MODEL=(.+)$" -ErrorAction SilentlyContinue
    if ($matchModel) { $ollamaModel = $matchModel.Matches[0].Groups[1].Value.Trim() }
}

if ($llmProvider -eq "ollama") {
    Write-Step "Comprobando Ollama"

    function Test-OllamaUp {
        try {
            Invoke-WebRequest -Uri "http://localhost:11434" -UseBasicParsing -TimeoutSec 2 | Out-Null
            return $true
        } catch { return $false }
    }

    if (Test-OllamaUp) {
        Write-Host "Ollama ya responde en http://localhost:11434" -ForegroundColor Green
    } else {
        Write-Host "Ollama no responde. Arrancando 'ollama serve' en segundo plano..." -ForegroundColor Yellow
        $ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
        if (-not $ollamaCmd) {
            Write-Host "Aviso: no se encontró 'ollama' en el PATH. Instálalo desde https://ollama.com" -ForegroundColor Yellow
            Write-Host "o cambia LLM_PROVIDER=openai en backend/.env." -ForegroundColor Yellow
        } else {
            Start-Process -FilePath $ollamaCmd.Source -ArgumentList "serve" -WindowStyle Hidden
            $deadline = (Get-Date).AddSeconds(20)
            $up = $false
            while ((Get-Date) -lt $deadline) {
                if (Test-OllamaUp) { $up = $true; break }
                Start-Sleep -Milliseconds 500
            }
            if ($up) {
                Write-Host "Ollama arrancado y respondiendo en http://localhost:11434" -ForegroundColor Green
            } else {
                Write-Host "Aviso: Ollama no respondió tras 20s. Revisa manualmente ('ollama serve')." -ForegroundColor Yellow
            }
        }
    }

    if (Test-OllamaUp) {
        try {
            $tags = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 5
            $availableModels = $tags.models | ForEach-Object { $_.name }
            if ($availableModels -notcontains $ollamaModel -and ($availableModels | Where-Object { $_ -like "$ollamaModel*" }).Count -eq 0) {
                Write-Host "Aviso: el modelo '$ollamaModel' (OLLAMA_MODEL en .env) no está descargado." -ForegroundColor Yellow
                Write-Host "Modelos disponibles: $($availableModels -join ', ')" -ForegroundColor Yellow
                Write-Host "Ejecuta: ollama pull $ollamaModel" -ForegroundColor Yellow
            } else {
                Write-Host "Modelo '$ollamaModel' disponible." -ForegroundColor Green
            }
        } catch {
            Write-Host "Aviso: no se pudo comprobar la lista de modelos de Ollama." -ForegroundColor Yellow
        }
    }
}

# --- Lanzar backend y frontend en ventanas separadas (log visible en vivo) ---
# Se usa `start powershell -NoExit` (una ventana real por proceso) en vez de
# Start-Process -NoNewWindow: con -NoNewWindow el stdout de uvicorn/ng queda
# unido al del script lanzador y, si éste corre embebido o se lanza desde otra
# ventana, ese output no es visible en ningún sitio y no hay forma de
# diagnosticar un arranque colgado (p.ej. ng serve tardando en compilar).
Write-Step "Arrancando backend (http://localhost:8000) y frontend (http://localhost:4200)"

$backendCmd = "cd '$backendDir'; & '$venvPython' -m uvicorn app.main:app --reload --port 8000"
Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", $backendCmd -WindowStyle Normal

$frontendCmd = "cd '$frontendDir'; npm start"
Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", $frontendCmd -WindowStyle Normal

Write-Host ""
Write-Host "Backend y frontend arrancando cada uno en su propia ventana de PowerShell." -ForegroundColor Green
Write-Host "Cierra esas ventanas (o Ctrl+C dentro de ellas) para detenerlos." -ForegroundColor Green
Write-Host ""
Write-Step "Comprobando arranque"

function Wait-ForHttp($url, $label, $timeoutSec) {
    $deadline = (Get-Date).AddSeconds($timeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2
            if ($resp.StatusCode -eq 200) {
                Write-Host "$label listo en $url" -ForegroundColor Green
                return $true
            }
        } catch { Start-Sleep -Milliseconds 1000 }
    }
    Write-Host "Aviso: $label no respondió en $url tras ${timeoutSec}s (revisa su ventana de PowerShell)." -ForegroundColor Yellow
    return $false
}

Wait-ForHttp "http://localhost:8000/api/health" "Backend" 60 | Out-Null
Wait-ForHttp "http://localhost:4200" "Frontend" 90 | Out-Null
