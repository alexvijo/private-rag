"""Búsqueda web vía DuckDuckGo HTML (sin API key).

Usa el endpoint HTML de DuckDuckGo (html.duckduckgo.com/html/), pensado para
scraping sin JS, en vez de la API oficial (de pago) o el buscador JS normal.
No hay contrato ni SLA: si DuckDuckGo cambia su marcado HTML, esto puede
romperse — es la contrapartida de no requerir API key.
"""
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup

from app.generation.llm_client import LLMError

_SEARCH_URL = "https://html.duckduckgo.com/html/"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; private-rag/1.0)"}


@dataclass
class WebResult:
    title: str
    url: str
    snippet: str


async def search_web(query: str, max_results: int = 5) -> list[WebResult]:
    """Busca en DuckDuckGo y devuelve título, URL y snippet de cada resultado."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                _SEARCH_URL,
                data={"q": query},
                headers=_HEADERS,
                timeout=10,
            )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise LLMError(f"No se pudo realizar la búsqueda web: {exc}") from exc

    soup = BeautifulSoup(response.text, "html.parser")
    results: list[WebResult] = []
    for result in soup.select(".result"):
        link = result.select_one(".result__a")
        snippet_el = result.select_one(".result__snippet")
        if not link or not link.get("href"):
            continue
        results.append(
            WebResult(
                title=link.get_text(strip=True),
                url=link["href"],
                snippet=snippet_el.get_text(strip=True) if snippet_el else "",
            )
        )
        if len(results) >= max_results:
            break
    return results
