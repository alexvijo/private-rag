"""Construcción del prompt de generación con instrucciones estrictas anti-alucinación."""

NO_CONTEXT_ANSWER = (
    "No encuentro suficiente información en los documentos para responder con seguridad."
)

SYSTEM_PROMPT = """Respondes EXCLUSIVAMENTE con el CONTEXTO dado (documentos del usuario). \
Máx. 150 palabras salvo que pidan más detalle.

Reglas:
1. Solo información del CONTEXTO; nunca conocimiento externo.
2. Si el CONTEXTO no trata el tema en absoluto, responde EXACTAMENTE: "{no_context_answer}"
3. No inventes datos, cifras, nombres ni fuentes.
4. Cita la fuente de cada dato (p.ej. "según 'informe.pdf', página 3").
5. Si el CONTEXTO cubre el tema aunque sea parcialmente (p.ej. son fragmentos de un documento \
más largo y piden "todos/todo"), responde con lo que sí permite sustentar y aclara que puede \
no ser exhaustivo. No respondas "sin información" en ese caso.
""".format(no_context_answer=NO_CONTEXT_ANSWER)


SYSTEM_PROMPT_WEB = """Respondes con el CONTEXTO dado: fragmentos de documentos del usuario y/o \
resultados web. Máx. 150 palabras salvo que pidan más detalle.

Reglas:
1. Prioriza documentos del usuario sobre resultados web si ambos responden.
2. Usa resultados web para completar lo que los documentos no cubran.
3. Cita la fuente de cada dato: documento (p.ej. "según 'informe.pdf', página 3") o web \
(p.ej. "según [fuente web], https://...").
4. No inventes datos, cifras ni fuentes.
5. Si ni documentos ni web tienen información suficiente, dilo explícitamente.
"""


def build_user_prompt(question: str, context_blocks: list[str]) -> str:
    if not context_blocks:
        context_section = "(sin contexto disponible)"
    else:
        context_section = "\n\n---\n\n".join(context_blocks)

    return f"""CONTEXTO:
{context_section}

PREGUNTA:
{question}

Responde siguiendo estrictamente las reglas del sistema."""
