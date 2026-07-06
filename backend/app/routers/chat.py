"""Endpoint de chat: recibe una pregunta y devuelve respuesta + fuentes."""
import logging

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.dependencies import RagServiceDep
from app.generation.llm_client import LLMError
from app.models.schemas import ChatRequest, ChatResponse, ModelsResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, rag_service: RagServiceDep) -> ChatResponse:
    try:
        return await rag_service.answer_question(
            request.question,
            request.top_k,
            request.model,
            request.web_search,
            request.doc_ids,
        )
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error inesperado al generar respuesta")
        raise HTTPException(status_code=500, detail=f"Error interno: {exc}") from exc


@router.get("/models", response_model=ModelsResponse)
async def list_models(rag_service: RagServiceDep) -> ModelsResponse:
    """Lista los modelos disponibles en el proveedor LLM activo (solo Ollama expone listado)."""
    settings = get_settings()
    current_model = settings.ollama_model if settings.llm_provider.lower() == "ollama" else settings.openai_model
    try:
        available = await rag_service.list_available_models()
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return ModelsResponse(
        provider=settings.llm_provider,
        current_model=current_model,
        available_models=available,
    )
