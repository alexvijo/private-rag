"""Wrapper sobre sentence-transformers para generar embeddings localmente.

Usar un modelo local evita depender de una API externa (y su coste) solo
para vectorizar texto; el LLM de generación sí puede ser remoto si se desea.
"""
from functools import lru_cache

from sentence_transformers import SentenceTransformer


class Embedder:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = SentenceTransformer(model_name)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Genera embeddings normalizados para una lista de textos."""
        if not texts:
            return []
        vectors = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return vectors.tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]


@lru_cache
def get_embedder(model_name: str) -> Embedder:
    """Cachea el modelo de embeddings en memoria (carga costosa, una sola vez)."""
    return Embedder(model_name)
