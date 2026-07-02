"""Divide texto en chunks semánticos con solapamiento configurable.

Estrategia recursiva por separadores jerárquicos (párrafo -> línea -> frase ->
palabra), similar al RecursiveCharacterTextSplitter de LangChain, pero
implementada sin dependencias extra.
"""
from dataclasses import dataclass

from app.ingestion.parsers import ExtractedSegment

_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


@dataclass
class Chunk:
    text: str
    location: str
    chunk_index: int


def _split_text(text: str, chunk_size: int, separators: list[str]) -> list[str]:
    """Divide `text` recursivamente probando separadores de mayor a menor granularidad."""
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    if not separators:
        # Último recurso: corte duro por longitud
        return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]

    sep, *rest = separators
    if sep == "":
        return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]

    parts = text.split(sep)
    chunks: list[str] = []
    current = ""
    for part in parts:
        candidate = current + sep + part if current else part
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                chunks.append(current)
            if len(part) > chunk_size:
                chunks.extend(_split_text(part, chunk_size, rest))
                current = ""
            else:
                current = part
    if current:
        chunks.append(current)
    return [c for c in chunks if c.strip()]


def _apply_overlap(pieces: list[str], chunk_size: int, chunk_overlap: int) -> list[str]:
    """Añade solapamiento entre chunks consecutivos tomando el final del anterior."""
    if chunk_overlap <= 0 or len(pieces) <= 1:
        return pieces

    overlapped = [pieces[0]]
    for piece in pieces[1:]:
        prev = overlapped[-1]
        overlap_text = prev[-chunk_overlap:] if len(prev) > chunk_overlap else prev
        merged = (overlap_text + " " + piece).strip()
        # Evitar que el solapamiento haga crecer el chunk desmesuradamente
        overlapped.append(merged[: chunk_size + chunk_overlap])
    return overlapped


def chunk_segments(
    segments: list[ExtractedSegment],
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> list[Chunk]:
    """Convierte segmentos extraídos de un documento en chunks indexables."""
    chunks: list[Chunk] = []
    index = 0
    for segment in segments:
        raw_pieces = _split_text(segment.text, chunk_size, _SEPARATORS)
        pieces = _apply_overlap(raw_pieces, chunk_size, chunk_overlap)
        for piece in pieces:
            chunks.append(Chunk(text=piece, location=segment.location, chunk_index=index))
            index += 1
    return chunks
