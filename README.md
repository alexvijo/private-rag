# RAG Chat — Chat inteligente sobre tus documentos

Aplicación RAG (Retrieval-Augmented Generation) completa y lista para ejecutar: sube documentos
PDF, DOCX, XLSX, TXT o CSV, y haz preguntas sobre su contenido. El asistente responde
**exclusivamente** con información encontrada en tus documentos, citando las fuentes exactas, y
declara explícitamente cuando no tiene suficiente información.

Flujo implementado: **cargar documento → parsear → dividir en chunks con solapamiento → generar
embeddings → indexar en vector store persistente → recuperar contexto relevante → generar
respuesta con un prompt estricto anti-alucinación**.

## Stack técnico

| Capa | Tecnología | Por qué |
|---|---|---|
| Backend | **Python + FastAPI** | El ecosistema de parsing/RAG (pypdf, python-docx, openpyxl, chromadb, sentence-transformers) es nativamente Python. FastAPI aporta tipado, docs automáticas (OpenAPI) y async nativo. |
| Frontend | **Angular 18** (standalone components + signals) | Pedido explícito del proyecto; arquitectura modular con servicios tipados y componentes independientes. |
| Vector store | **ChromaDB** (persistente en disco) | Persiste automáticamente, soporta borrado/filtrado por metadata (`doc_id`), ideal para CRUD de documentos individuales. |
| Embeddings | **sentence-transformers** (`all-MiniLM-L6-v2`) | Modelo local, gratuito, rápido y sin necesidad de API key. |
| LLM | **Ollama** (por defecto, local y gratis) u **OpenAI** | Seleccionable por variable de entorno `LLM_PROVIDER`, sin tocar código. |

## Arquitectura

```
private-rag/
├── backend/                     # API FastAPI
│   ├── app/
│   │   ├── main.py              # App FastAPI, CORS, startup
│   │   ├── config.py            # Configuración vía variables de entorno
│   │   ├── dependencies.py      # Inyección de dependencias (singleton RagService)
│   │   ├── models/schemas.py    # Modelos Pydantic (request/response)
│   │   ├── ingestion/
│   │   │   ├── parsers.py       # Extracción de texto: PDF, DOCX, XLSX, TXT, CSV
│   │   │   └── chunking.py      # Text splitter recursivo con overlap
│   │   ├── embeddings/
│   │   │   └── embedder.py      # Wrapper de sentence-transformers
│   │   ├── vectorstore/
│   │   │   └── chroma_store.py  # Acceso a ChromaDB (add/query/delete)
│   │   ├── generation/
│   │   │   ├── llm_client.py    # Cliente LLM (Ollama / OpenAI, intercambiable)
│   │   │   └── prompt.py        # Prompt estricto anti-alucinación
│   │   ├── routers/
│   │   │   ├── documents.py     # Endpoints: upload, list, delete, reindex
│   │   │   └── chat.py          # Endpoint: chat
│   │   └── services/
│   │       └── rag_service.py   # Orquesta todo el flujo RAG
│   ├── data/                    # uploads/ + chroma_db/ (persistente, gitignored)
│   ├── requirements.txt
│   └── .env.example
├── frontend/                    # Angular 18 (standalone)
│   └── src/app/
│       ├── core/
│       │   ├── models/          # Interfaces TS compartidas
│       │   └── services/        # document.service.ts, chat.service.ts
│       └── features/
│           ├── chat/            # Ventana de chat con citación de fuentes
│           └── documents/       # Panel de subida/gestión de documentos
├── sample_docs/                 # Documentos de prueba (PDF, DOCX, XLSX, TXT, CSV)
├── docker-compose.yml
└── README.md
```

## Instalación y ejecución

### Requisitos previos

- **Python 3.11+**
- **Node.js 20+** y npm
- **Ollama** (opción por defecto, 100% local y gratis) → [ollama.com](https://ollama.com), o una **API key de OpenAI** si prefieres usar `LLM_PROVIDER=openai`

### 1. Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# Edita .env si quieres cambiar el proveedor de LLM u otros parámetros

uvicorn app.main:app --reload --port 8000
```

La API queda disponible en `http://localhost:8000` (documentación interactiva en
`http://localhost:8000/docs`).

**Si usas Ollama** (por defecto), en otra terminal:

```bash
ollama pull llama3.2
ollama serve      # normalmente ya se ejecuta como servicio tras instalar Ollama
```

**Si prefieres OpenAI**, edita `backend/.env`:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

### 2. Frontend

```bash
cd frontend
npm install
npm start
```

La aplicación queda disponible en `http://localhost:4200`.

### 3. Con Docker Compose (backend + frontend)

```bash
docker compose up --build
```

- Frontend: `http://localhost:4200`
- Backend: `http://localhost:8000`

Por defecto usa Ollama ejecutándose en el host (`host.docker.internal:11434`). Para usar OpenAI,
define `LLM_PROVIDER=openai` y `OPENAI_API_KEY` como variables de entorno antes de levantar los
contenedores.

## Ejemplo de uso

1. Abre `http://localhost:4200`.
2. Arrastra a la barra lateral los archivos de `sample_docs/` (o los tuyos propios):
   - `politica_vacaciones.txt`
   - `catalogo_productos.csv`
   - `manual_onboarding.docx`
   - `informe_ventas.xlsx`
   - `especificaciones_producto.pdf`
3. Espera a que aparezcan en la lista de "Documentos" (indica cuántos chunks se generaron).
4. Pregunta en el chat, por ejemplo:
   - *"¿Cuántos días de vacaciones tengo al año?"* → responde con base en `politica_vacaciones.txt`.
   - *"¿Qué precio tiene el monitor 4K?"* → responde con base en `catalogo_productos.csv`.
   - *"¿Cuál es la capital de Francia?"* → responde: *"No encuentro suficiente información en
     los documentos para responder con seguridad."* (pregunta fuera de contexto).
5. Haz clic en "Ver fuentes" bajo cualquier respuesta para ver los fragmentos exactos usados.
6. Usa "Reindexar todo" tras cambiar `CHUNK_SIZE`/`CHUNK_OVERLAP` en `.env`, o "Borrar índice"
   para empezar de cero.

## Variables de entorno principales (`backend/.env`)

| Variable | Descripción | Por defecto |
|---|---|---|
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | Tamaño de chunk y solapamiento (caracteres) | `1000` / `150` |
| `EMBEDDING_MODEL` | Modelo de sentence-transformers | `all-MiniLM-L6-v2` |
| `TOP_K` | Nº de chunks recuperados por pregunta | `4` |
| `LLM_PROVIDER` | `ollama` u `openai` | `ollama` |
| `OLLAMA_MODEL` | Modelo servido por Ollama | `llama3.2` |
| `OPENAI_MODEL` | Modelo de OpenAI (si aplica) | `gpt-4o-mini` |
| `LLM_TEMPERATURE` | Temperatura de generación | `0.1` |

## Endpoints principales

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/documents/upload` | Sube uno o varios archivos (multipart), los indexa |
| `GET` | `/api/documents` | Lista documentos indexados |
| `DELETE` | `/api/documents/{doc_id}` | Elimina un documento y sus chunks |
| `POST` | `/api/documents/reindex` | Reindexa todos los documentos ya subidos |
| `DELETE` | `/api/documents` | Borra completamente el índice |
| `POST` | `/api/chat` | `{ "question": "...", "top_k": 4 }` → respuesta + fuentes |
| `GET` | `/api/health` | Estado del servicio, proveedor LLM activo, nº de documentos/chunks |

## Comportamiento anti-alucinación

El prompt de sistema (`backend/app/generation/prompt.py`) instruye al LLM a:

1. Usar **solo** el contexto recuperado, nunca conocimiento externo.
2. Responder literalmente *"No encuentro suficiente información en los documentos para responder
   con seguridad."* si el contexto no basta.
3. Citar el documento/fragmento de origen al afirmar datos concretos.

Además, `rag_service.py` aplica un **umbral mínimo de similitud coseno** (`MIN_RELEVANCE_SCORE =
0.15`): si ningún chunk recuperado supera ese umbral, ni siquiera se llama al LLM — se devuelve
directamente la respuesta de "sin contexto", evitando alucinaciones por chunks irrelevantes.

## Recomendaciones de mejoras futuras

- **Streaming de respuestas** (Server-Sent Events) para mostrar tokens a medida que se generan.
- **Autenticación de usuarios** y multi-tenancy (índices separados por usuario/organización).
- **Re-ranking** de los chunks recuperados con un cross-encoder antes de pasar al LLM.
- **Chunking semántico** basado en embeddings (en vez de solo separadores de caracteres).
- **Soporte para más formatos**: PPTX, Markdown, HTML, imágenes con OCR.
- **Historial de conversación** con memoria contextual (RAG conversacional multi-turno).
- **Observabilidad**: métricas de latencia, tasa de "sin contexto", logging estructurado.
- **Tests automatizados** (pytest para backend, Jasmine/Karma o Vitest para frontend).
- **CI/CD**: pipeline de GitHub Actions para lint, tests y build en cada PR.
- **Despliegue en producción**: backend detrás de un proxy con HTTPS, vector store gestionado
  (Chroma Cloud, Qdrant, pgvector) para escalar más allá de un único proceso.
