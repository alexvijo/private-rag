#!/usr/bin/env bash
# Levanta el backend (FastAPI) y el frontend (Angular) en paralelo para desarrollo
# local, sin Docker. Crea el entorno virtual e instala dependencias si hace falta.
#
# Uso:
#   ./start.sh                 # backend + frontend
#   SKIP_INSTALL=1 ./start.sh  # omite pip install / npm install (arranque rápido)

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

step() { echo -e "\n==> $1"; }

# --- Backend: venv + dependencias ---
step "Preparando backend"

VENV_DIR="$BACKEND_DIR/venv"
VENV_PYTHON="$VENV_DIR/bin/python"

if [ ! -x "$VENV_PYTHON" ]; then
    echo "Creando entorno virtual en backend/venv ..."
    python3 -m venv "$VENV_DIR"
fi

if [ -z "${SKIP_INSTALL:-}" ]; then
    echo "Instalando dependencias del backend (pip install -r requirements.txt) ..."
    "$VENV_PYTHON" -m pip install --quiet --upgrade pip
    "$VENV_PYTHON" -m pip install --quiet -r "$BACKEND_DIR/requirements.txt"
fi

ENV_FILE="$BACKEND_DIR/.env"
ENV_EXAMPLE="$BACKEND_DIR/.env.example"
if [ ! -f "$ENV_FILE" ] && [ -f "$ENV_EXAMPLE" ]; then
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    echo "Creado backend/.env a partir de .env.example (ajusta LLM_PROVIDER si hace falta)."
fi

# --- Frontend: node_modules ---
step "Preparando frontend"

if [ -z "${SKIP_INSTALL:-}" ] && [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "Instalando dependencias del frontend (npm install) ..."
    (cd "$FRONTEND_DIR" && npm install)
fi

# --- Comprobación de Ollama (si es el proveedor configurado) ---
LLM_PROVIDER="ollama"
if [ -f "$ENV_FILE" ]; then
    match=$(grep -E "^LLM_PROVIDER=" "$ENV_FILE" || true)
    if [ -n "$match" ]; then
        LLM_PROVIDER="${match#LLM_PROVIDER=}"
    fi
fi

if [ "$LLM_PROVIDER" = "ollama" ]; then
    step "Comprobando Ollama"
    if curl -s -o /dev/null -m 2 http://localhost:11434; then
        echo "Ollama responde en http://localhost:11434"
    else
        echo "Aviso: Ollama no responde en http://localhost:11434."
        echo "Instala/arranca Ollama (https://ollama.com) y ejecuta 'ollama pull llama3.2',"
        echo "o cambia LLM_PROVIDER=openai en backend/.env."
    fi
fi

# --- Lanzar backend y frontend en paralelo ---
step "Arrancando backend (http://localhost:8000) y frontend (http://localhost:4200)"

cleanup() {
    echo -e "\nDeteniendo backend y frontend..."
    [ -n "${BACKEND_PID:-}" ] && kill "$BACKEND_PID" 2>/dev/null || true
    [ -n "${FRONTEND_PID:-}" ] && kill "$FRONTEND_PID" 2>/dev/null || true
    wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

(cd "$BACKEND_DIR" && "$VENV_PYTHON" -m uvicorn app.main:app --reload --port 8000) &
BACKEND_PID=$!

(cd "$FRONTEND_DIR" && npm start) &
FRONTEND_PID=$!

echo -e "\nBackend y frontend arrancando (Ctrl+C para detener ambos)...\n"
wait
