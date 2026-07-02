"""Inyección de dependencias de FastAPI: instancia única de RagService."""
from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.config import get_settings
from app.services.rag_service import RagService


@lru_cache
def get_rag_service() -> RagService:
    """Instancia única (singleton) de RagService, cacheada en memoria del proceso."""
    return RagService(get_settings())


RagServiceDep = Annotated[RagService, Depends(get_rag_service)]
