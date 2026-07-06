"""Endpoints para subir, listar, borrar y reindexar documentos."""
import asyncio
import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.dependencies import RagServiceDep
from app.ingestion.parsers import DocumentParseError, UnsupportedFileTypeError, SUPPORTED_EXTENSIONS
from app.models.schemas import (
    DeleteResponse,
    DocumentListResponse,
    ReindexResponse,
    UploadResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload", response_model=UploadResponse)
async def upload_documents(rag_service: RagServiceDep, files: list[UploadFile] = File(...)) -> UploadResponse:
    """Sube uno o varios documentos, los parsea, chunkea, embede e indexa."""
    indexed = []
    errors = []

    for file in files:
        try:
            content = await file.read()
            if not content:
                errors.append(f"{file.filename}: el archivo está vacío.")
                continue

            # Parseo + chunking + embeddings son CPU-bound y pueden tardar
            # decenas de segundos con documentos grandes; se ejecutan en un
            # thread aparte para no bloquear el event loop (y así el chat u
            # otras peticiones pueden seguir atendiéndose mientras se indexa).
            info = await asyncio.to_thread(rag_service.ingest_file, file.filename, content)
            indexed.append(info)
        except UnsupportedFileTypeError as exc:
            errors.append(f"{file.filename}: {exc}")
        except DocumentParseError as exc:
            errors.append(f"{file.filename}: {exc}")
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error inesperado al indexar %s", file.filename)
            errors.append(f"{file.filename}: error inesperado ({exc})")

    return UploadResponse(indexed=indexed, errors=errors)


@router.get("", response_model=DocumentListResponse)
async def list_documents(rag_service: RagServiceDep) -> DocumentListResponse:
    return DocumentListResponse(documents=rag_service.list_documents())


@router.delete("/{doc_id}", response_model=DeleteResponse)
async def delete_document(doc_id: str, rag_service: RagServiceDep) -> DeleteResponse:
    deleted = rag_service.delete_document(doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Documento '{doc_id}' no encontrado.")
    return DeleteResponse(deleted=True, doc_id=doc_id)


@router.post("/reindex", response_model=ReindexResponse)
async def reindex_documents(rag_service: RagServiceDep) -> ReindexResponse:
    """Borra el índice vectorial y reindexa todos los documentos ya subidos."""
    doc_count, chunk_count = await asyncio.to_thread(rag_service.reindex_all)
    return ReindexResponse(reindexed_documents=doc_count, total_chunks=chunk_count)


@router.delete("", response_model=dict)
async def clear_all_documents(rag_service: RagServiceDep) -> dict:
    """Borra completamente el índice y todos los documentos subidos."""
    rag_service.clear_index()
    return {"cleared": True}


@router.get("/supported-formats", response_model=list[str])
async def supported_formats() -> list[str]:
    return sorted(SUPPORTED_EXTENSIONS)
