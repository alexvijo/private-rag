"""Modelos Pydantic para requests y responses de la API."""
from datetime import datetime

from pydantic import BaseModel, Field


class DocumentInfo(BaseModel):
    """Información de un documento indexado."""

    doc_id: str
    filename: str
    file_type: str
    chunk_count: int
    uploaded_at: datetime
    size_bytes: int


class UploadResponse(BaseModel):
    """Resultado de subir e indexar uno o más documentos."""

    indexed: list[DocumentInfo]
    errors: list[str] = Field(default_factory=list)


class DocumentListResponse(BaseModel):
    documents: list[DocumentInfo]


class DeleteResponse(BaseModel):
    deleted: bool
    doc_id: str


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    top_k: int | None = Field(default=None, ge=1, le=20)
    model: str | None = Field(default=None, description="Override del modelo LLM para esta pregunta")
    web_search: bool = Field(
        default=False,
        description="Si es true, añade resultados de búsqueda web al contexto y permite al "
        "modelo usar conocimiento fuera de los documentos.",
    )
    doc_ids: list[str] | None = Field(
        default=None,
        description="Si se indica, el retrieval se limita a estos documentos "
        "(p.ej. los seleccionados por checkbox en el panel de documentos).",
    )


class SourceChunk(BaseModel):
    """Fragmento de un documento usado para sustentar una respuesta."""

    doc_id: str
    filename: str
    chunk_index: int
    text: str
    score: float
    location: str | None = None  # p.ej. "página 3" o "hoja Ventas"


class WebSource(BaseModel):
    """Resultado web usado para sustentar una respuesta."""

    title: str
    url: str
    snippet: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    web_sources: list[WebSource] = Field(default_factory=list)
    has_sufficient_context: bool


class ReindexResponse(BaseModel):
    reindexed_documents: int
    total_chunks: int


class HealthResponse(BaseModel):
    status: str
    llm_provider: str
    llm_model: str
    llm_reachable: bool
    documents_indexed: int
    total_chunks: int


class ModelsResponse(BaseModel):
    provider: str
    current_model: str
    available_models: list[str] = Field(default_factory=list)
