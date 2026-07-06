"""Configuración centralizada de la aplicación vía variables de entorno."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Servidor
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "http://localhost:4200"

    # Almacenamiento
    upload_dir: str = "./data/uploads"
    chroma_persist_dir: str = "./data/chroma_db"
    collection_name: str = "rag_documents"

    # Chunking
    chunk_size: int = 1000
    chunk_overlap: int = 150

    # Embeddings
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Retrieval
    top_k: int = 6

    # LLM
    llm_provider: str = "ollama"  # "ollama" | "openai"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Generación
    llm_temperature: float = 0.1
    max_context_tokens: int = 8000

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def chroma_path(self) -> Path:
        path = Path(self.chroma_persist_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    """Devuelve una instancia cacheada de la configuración."""
    return Settings()
