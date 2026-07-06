"""Cliente LLM abstracto con implementaciones para Ollama (local) y OpenAI.

El proveedor se selecciona por la variable de entorno LLM_PROVIDER, sin
necesidad de tocar código. Ollama es el valor por defecto porque es 100%
local y gratuito (no requiere API key).
"""
from abc import ABC, abstractmethod
from functools import lru_cache

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import Settings

# Cliente HTTP compartido: reutiliza el pool de conexiones entre requests en
# vez de abrir un socket TCP nuevo por cada llamada al LLM.
_http_client = httpx.AsyncClient(timeout=120)


class LLMError(Exception):
    """Error al comunicarse con el proveedor de LLM."""


class LLMClient(ABC):
    @abstractmethod
    async def generate(self, system_prompt: str, user_prompt: str, temperature: float) -> str:
        """Genera una respuesta de texto a partir del prompt de sistema y usuario."""


class OllamaClient(LLMClient):
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=4))
    async def generate(self, system_prompt: str, user_prompt: str, temperature: float) -> str:
        try:
            response = await _http_client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "stream": False,
                    "options": {"temperature": temperature},
                },
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"].strip()
        except httpx.ConnectError as exc:
            raise LLMError(
                f"No se pudo conectar con Ollama en {self.base_url}. "
                "¿Está Ollama instalado y ejecutándose? (https://ollama.com)"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise LLMError(
                f"Ollama devolvió un error: {exc.response.status_code}. "
                f"¿Descargaste el modelo '{self.model}'? Ejecuta: ollama pull {self.model}"
            ) from exc
        except (KeyError, ValueError) as exc:
            raise LLMError(f"Respuesta inesperada de Ollama: {exc}") from exc

    async def list_models(self) -> list[str]:
        """Consulta los modelos disponibles en el servidor Ollama activo (`ollama list`)."""
        try:
            response = await _http_client.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            data = response.json()
            return sorted(m["name"] for m in data.get("models", []))
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise LLMError(f"No se pudo listar los modelos de Ollama: {exc}") from exc


class OpenAIClient(LLMClient):
    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise LLMError(
                "LLM_PROVIDER=openai requiere OPENAI_API_KEY configurada en el archivo .env"
            )
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=4))
    async def generate(self, system_prompt: str, user_prompt: str, temperature: float) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return (response.choices[0].message.content or "").strip()
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"Error al llamar a OpenAI: {exc}") from exc


@lru_cache
def _build_llm_client(provider: str, base_url: str, api_key: str, model: str) -> LLMClient:
    if provider == "ollama":
        return OllamaClient(base_url, model)
    if provider == "openai":
        return OpenAIClient(api_key, model)
    raise LLMError(f"LLM_PROVIDER desconocido: '{provider}'. Usa 'ollama' u 'openai'.")


def get_llm_client(settings: Settings, model_override: str | None = None) -> LLMClient:
    """Factory que instancia (y cachea) el cliente LLM según LLM_PROVIDER.

    Cachear por (provider, modelo) evita reconstruir el cliente (y, en el
    caso de OpenAI, su pool HTTP interno) en cada request. `model_override`
    permite elegir un modelo distinto al de .env para una request puntual
    (p.ej. el selector de modelos en el frontend), con su propia entrada
    cacheada.
    """
    provider = settings.llm_provider.lower()
    model = model_override or (
        settings.ollama_model if provider == "ollama" else settings.openai_model
    )
    return _build_llm_client(provider, settings.ollama_base_url, settings.openai_api_key, model)
