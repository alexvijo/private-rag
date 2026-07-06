"""Punto de entrada de la aplicación FastAPI."""
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.dependencies import get_rag_service
from app.models.schemas import HealthResponse
from app.routers import chat, documents

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="RAG Chat API",
    description="API para chat inteligente sobre documentos propios (PDF, DOCX, XLSX, TXT, CSV).",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(chat.router)


@app.on_event("startup")
async def startup_event() -> None:
    """Precarga el servicio RAG (y el modelo de embeddings) al arrancar."""
    logger.info("Inicializando RagService (esto puede tardar unos segundos la primera vez)...")
    get_rag_service()
    logger.info("RagService listo. Proveedor LLM: %s", settings.llm_provider)


@app.get("/api/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    try:
        service = get_rag_service()
        doc_count, chunk_count = service.stats()
        llm_reachable = await service.check_llm_reachable()
        model_name = settings.ollama_model if settings.llm_provider.lower() == "ollama" else settings.openai_model
        return HealthResponse(
            status="ok" if llm_reachable else "degraded",
            llm_provider=settings.llm_provider,
            llm_model=model_name,
            llm_reachable=llm_reachable,
            documents_indexed=doc_count,
            total_chunks=chunk_count,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Servicio no disponible: {exc}") from exc


@app.get("/")
async def root() -> dict:
    return {"message": "RAG Chat API", "docs": "/docs", "health": "/api/health"}
