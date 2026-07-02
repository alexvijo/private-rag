"""Endpoint de chat: recibe una pregunta y devuelve respuesta + fuentes."""
import logging

from fastapi import APIRouter, HTTPException

from app.dependencies import RagServiceDep
from app.generation.llm_client import LLMError
from app.models.schemas import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, rag_service: RagServiceDep) -> ChatResponse:
    try:
        return rag_service.answer_question(request.question, request.top_k)
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error inesperado al generar respuesta")
        raise HTTPException(status_code=500, detail=f"Error interno: {exc}") from exc
