"""Conteo de tokens para dimensionar el contexto enviado al LLM.

Se usa el tokenizador de tiktoken (cl100k_base) como aproximación estándar.
No es exacto para modelos que no son de OpenAI (p.ej. Llama vía Ollama), pero
da una estimación mucho más fiable que contar caracteres, evitando tanto
desperdiciar ventana de contexto como excederla.
"""
import tiktoken

_encoding = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_encoding.encode(text))
