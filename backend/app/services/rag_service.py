"""Orquesta el flujo completo de RAG: ingestión, indexación, retrieval y generación.

Flujo (imitando el tutorial clásico de RAG):
  1. Cargar documento -> parsear a texto.
  2. Partir en chunks con solapamiento.
  3. Crear embeddings de cada chunk.
  4. Indexar en el vector store persistente.
  5. Ante una pregunta: embeder la pregunta, recuperar los chunks más relevantes.
  6. Construir un prompt estricto con ese contexto y generar la respuesta final.
"""
import asyncio
import logging
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.config import Settings
from app.embeddings.embedder import get_embedder
from app.generation.llm_client import LLMError, get_llm_client
from app.generation.prompt import (
    NO_CONTEXT_ANSWER,
    SYSTEM_PROMPT,
    SYSTEM_PROMPT_WEB,
    build_user_prompt,
)
from app.generation.token_counter import count_tokens
from app.generation.web_search import search_web
from app.ingestion.chunking import chunk_segments
from app.ingestion.parsers import (
    DocumentParseError,
    UnsupportedFileTypeError,
    parse_document,
)
from app.models.schemas import ChatResponse, DocumentInfo, SourceChunk, WebSource
from app.vectorstore.chroma_store import ChromaStore

logger = logging.getLogger(__name__)

# Umbral mínimo de similitud coseno para considerar un chunk "relevante".
# Por debajo de esto, se asume que la pregunta está fuera del contexto de los documentos.
MIN_RELEVANCE_SCORE = 0.15


@dataclass
class DocumentRegistryEntry:
    doc_id: str
    filename: str
    file_type: str
    chunk_count: int
    uploaded_at: datetime
    size_bytes: int
    stored_path: str


class RagService:
    """Servicio principal, con estado en memoria del registro de documentos
    (respaldado por lo que ya existe en el vector store al arrancar)."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.embedder = get_embedder(settings.embedding_model)
        self.store = ChromaStore(str(settings.chroma_path), settings.collection_name)
        self._registry: dict[str, DocumentRegistryEntry] = {}
        self._load_registry_from_disk()

    # ------------------------------------------------------------------ #
    # Registro de documentos (metadata persistida como archivos + Chroma)
    # ------------------------------------------------------------------ #
    def _load_registry_from_disk(self) -> None:
        """Reconstruye el registro a partir de los archivos ya subidos, para
        no perder metadata entre reinicios del servidor."""
        upload_dir = self.settings.upload_path
        for doc_id in self.store.list_doc_ids():
            matches = list(upload_dir.glob(f"{doc_id}__*"))
            if not matches:
                continue
            stored_path = matches[0]
            original_name = stored_path.name.split("__", 1)[1]
            stat = stored_path.stat()
            self._registry[doc_id] = DocumentRegistryEntry(
                doc_id=doc_id,
                filename=original_name,
                file_type=stored_path.suffix.lstrip("."),
                chunk_count=self.store.count_chunks(doc_id),
                uploaded_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                size_bytes=stat.st_size,
                stored_path=str(stored_path),
            )

    # ------------------------------------------------------------------ #
    # Ingesta e indexación
    # ------------------------------------------------------------------ #
    def ingest_file(self, filename: str, content: bytes) -> DocumentInfo:
        """Guarda, parsea, chunkea, embede e indexa un único archivo."""
        doc_id = uuid.uuid4().hex[:12]
        safe_name = Path(filename).name  # evita path traversal
        stored_path = self.settings.upload_path / f"{doc_id}__{safe_name}"
        stored_path.write_bytes(content)

        try:
            segments = parse_document(stored_path)
            chunks = chunk_segments(
                segments,
                chunk_size=self.settings.chunk_size,
                chunk_overlap=self.settings.chunk_overlap,
            )
            if not chunks:
                raise DocumentParseError("No se generaron chunks: el documento parece vacío.")

            texts = [c.text for c in chunks]
            embeddings = self.embedder.embed_texts(texts)
            self.store.add_chunks(
                doc_id=doc_id,
                filename=safe_name,
                chunk_texts=texts,
                chunk_embeddings=embeddings,
                chunk_locations=[c.location for c in chunks],
            )
        except (UnsupportedFileTypeError, DocumentParseError):
            stored_path.unlink(missing_ok=True)
            raise
        except Exception:
            stored_path.unlink(missing_ok=True)
            raise

        entry = DocumentRegistryEntry(
            doc_id=doc_id,
            filename=safe_name,
            file_type=stored_path.suffix.lstrip("."),
            chunk_count=len(chunks),
            uploaded_at=datetime.now(timezone.utc),
            size_bytes=len(content),
            stored_path=str(stored_path),
        )
        self._registry[doc_id] = entry
        logger.info("Indexado '%s' (%d chunks)", safe_name, len(chunks))
        return self._to_document_info(entry)

    def list_documents(self) -> list[DocumentInfo]:
        return [self._to_document_info(e) for e in self._registry.values()]

    def delete_document(self, doc_id: str) -> bool:
        if doc_id not in self._registry:
            return False
        entry = self._registry.pop(doc_id)
        self.store.delete_document(doc_id)
        Path(entry.stored_path).unlink(missing_ok=True)
        return True

    def reindex_all(self) -> tuple[int, int]:
        """Borra el índice completo y reindexa todos los archivos ya subidos
        (útil tras cambiar CHUNK_SIZE/CHUNK_OVERLAP o el modelo de embeddings)."""
        entries = list(self._registry.values())
        self.store.clear_all()
        self._registry.clear()

        total_chunks = 0
        for entry in entries:
            content = Path(entry.stored_path).read_bytes()
            original_path = Path(entry.stored_path)
            original_path.unlink(missing_ok=True)
            info = self.ingest_file(entry.filename, content)
            total_chunks += info.chunk_count
        return len(entries), total_chunks

    def clear_index(self) -> None:
        """Borra completamente el índice y los archivos subidos."""
        self.store.clear_all()
        for entry in self._registry.values():
            Path(entry.stored_path).unlink(missing_ok=True)
        self._registry.clear()

    @staticmethod
    def _to_document_info(entry: DocumentRegistryEntry) -> DocumentInfo:
        return DocumentInfo(
            doc_id=entry.doc_id,
            filename=entry.filename,
            file_type=entry.file_type,
            chunk_count=entry.chunk_count,
            uploaded_at=entry.uploaded_at,
            size_bytes=entry.size_bytes,
        )

    # ------------------------------------------------------------------ #
    # Retrieval + generación
    # ------------------------------------------------------------------ #
    def _retrieve(self, question: str, k: int, doc_ids: list[str] | None) -> list:
        """Embede la pregunta y consulta el vector store (CPU-bound; se ejecuta
        en un thread aparte para no bloquear el event loop)."""
        query_embedding = self.embedder.embed_query(question)
        return self.store.query(query_embedding, top_k=k, doc_ids=doc_ids)

    async def answer_question(
        self,
        question: str,
        top_k: int | None = None,
        model: str | None = None,
        web_search: bool = False,
        doc_ids: list[str] | None = None,
    ) -> ChatResponse:
        k = top_k or self.settings.top_k

        # Retrieval local (CPU) y búsqueda web (red) son independientes:
        # lanzarlos en paralelo ahorra la latencia de red de DuckDuckGo antes
        # de poder construir el prompt.
        retrieve_task = asyncio.create_task(
            asyncio.to_thread(self._retrieve, question, k, doc_ids)
        )
        web_task = asyncio.create_task(search_web(question)) if web_search else None

        retrieved = await retrieve_task
        relevant = [r for r in retrieved if r.score >= MIN_RELEVANCE_SCORE]

        if not relevant and not web_search:
            return ChatResponse(
                answer=NO_CONTEXT_ANSWER,
                sources=[],
                has_sufficient_context=False,
            )

        context_blocks = []
        total_tokens = 0
        used_chunks = []
        for r in relevant:
            block = f"[Fuente: {r.filename}, {r.location}]\n{r.text}"
            block_tokens = count_tokens(block)
            if total_tokens + block_tokens > self.settings.max_context_tokens and used_chunks:
                break
            context_blocks.append(block)
            used_chunks.append(r)
            total_tokens += block_tokens

        web_results = []
        if web_task is not None:
            try:
                web_results = await web_task
            except LLMError as exc:
                logger.warning("Búsqueda web falló, continuando sin ella: %s", exc)
            for w in web_results:
                block = f"[Fuente web: {w.title}, {w.url}]\n{w.snippet}"
                block_tokens = count_tokens(block)
                if total_tokens + block_tokens > self.settings.max_context_tokens and context_blocks:
                    break
                context_blocks.append(block)
                total_tokens += block_tokens

        system_prompt = SYSTEM_PROMPT_WEB if web_search else SYSTEM_PROMPT
        user_prompt = build_user_prompt(question, context_blocks)

        try:
            llm = get_llm_client(self.settings, model_override=model)
            answer = await llm.generate(system_prompt, user_prompt, self.settings.llm_temperature)
        except LLMError as exc:
            logger.error("Error del LLM: %s", exc)
            raise

        is_no_context = not web_search and answer.strip() == NO_CONTEXT_ANSWER

        sources = [
            SourceChunk(
                doc_id=r.doc_id,
                filename=r.filename,
                chunk_index=r.chunk_index,
                text=r.text[:500],
                score=r.score,
                location=r.location,
            )
            for r in used_chunks
        ]
        web_sources = [
            WebSource(title=w.title, url=w.url, snippet=w.snippet) for w in web_results
        ]

        return ChatResponse(
            answer=answer,
            sources=[] if is_no_context else sources,
            web_sources=[] if is_no_context else web_sources,
            has_sufficient_context=not is_no_context,
        )

    def stats(self) -> tuple[int, int]:
        return len(self._registry), self.store.count_chunks()

    async def list_available_models(self) -> list[str]:
        """Modelos disponibles en el proveedor LLM actual (solo Ollama expone listado)."""
        if self.settings.llm_provider.lower() != "ollama":
            return []
        llm = get_llm_client(self.settings)
        return await llm.list_models()

    async def check_llm_reachable(self) -> bool:
        """Comprueba si el proveedor LLM configurado responde, sin generar texto."""
        try:
            if self.settings.llm_provider.lower() == "ollama":
                await get_llm_client(self.settings).list_models()
            return True
        except LLMError:
            return False
