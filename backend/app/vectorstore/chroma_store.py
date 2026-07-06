"""Capa de acceso al vector store persistente (ChromaDB).

ChromaDB se eligió sobre FAISS porque persiste automáticamente a disco y
soporta borrado por metadata (p.ej. "todos los chunks del doc_id X"), lo
cual simplifica mucho el reindexado y el borrado de documentos individuales.
"""
from dataclasses import dataclass

import chromadb
from chromadb.config import Settings as ChromaSettings


@dataclass
class RetrievedChunk:
    text: str
    doc_id: str
    filename: str
    chunk_index: int
    location: str
    score: float


class ChromaStore:
    def __init__(self, persist_dir: str, collection_name: str):
        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(
        self,
        doc_id: str,
        filename: str,
        chunk_texts: list[str],
        chunk_embeddings: list[list[float]],
        chunk_locations: list[str],
    ) -> None:
        if not chunk_texts:
            return
        ids = [f"{doc_id}::{i}" for i in range(len(chunk_texts))]
        metadatas = [
            {"doc_id": doc_id, "filename": filename, "chunk_index": i, "location": loc}
            for i, loc in enumerate(chunk_locations)
        ]
        self._collection.add(
            ids=ids,
            embeddings=chunk_embeddings,
            documents=chunk_texts,
            metadatas=metadatas,
        )

    def query(
        self,
        query_embedding: list[float],
        top_k: int,
        doc_ids: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        count = self._collection.count()
        if count == 0:
            return []
        where = {"doc_id": {"$in": doc_ids}} if doc_ids else None
        result = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, count),
            where=where,
        )
        chunks: list[RetrievedChunk] = []
        docs = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        for text, meta, distance in zip(docs, metadatas, distances):
            # Chroma con espacio "cosine" devuelve distancia; similarity = 1 - distance
            score = round(1 - distance, 4)
            chunks.append(
                RetrievedChunk(
                    text=text,
                    doc_id=meta["doc_id"],
                    filename=meta["filename"],
                    chunk_index=meta["chunk_index"],
                    location=meta.get("location", ""),
                    score=score,
                )
            )
        return chunks

    def delete_document(self, doc_id: str) -> None:
        self._collection.delete(where={"doc_id": doc_id})

    def clear_all(self) -> None:
        all_ids = self._collection.get()["ids"]
        if all_ids:
            self._collection.delete(ids=all_ids)

    def count_chunks(self, doc_id: str | None = None) -> int:
        if doc_id is None:
            return self._collection.count()
        return len(self._collection.get(where={"doc_id": doc_id})["ids"])

    def list_doc_ids(self) -> list[str]:
        metadatas = self._collection.get()["metadatas"]
        return sorted({m["doc_id"] for m in metadatas})
