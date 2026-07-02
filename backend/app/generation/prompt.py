"""Construcción del prompt de generación con instrucciones estrictas anti-alucinación."""

NO_CONTEXT_ANSWER = (
    "No encuentro suficiente información en los documentos para responder con seguridad."
)

SYSTEM_PROMPT = """Eres un asistente que responde preguntas EXCLUSIVAMENTE usando el CONTEXTO \
proporcionado, extraído de documentos subidos por el usuario.

Reglas estrictas:
1. Usa SOLO la información contenida en el CONTEXTO. Nunca uses conocimiento externo ni \
supuestos propios.
2. Si el CONTEXTO no contiene información suficiente para responder la pregunta, responde \
EXACTAMENTE: "{no_context_answer}"
3. No inventes datos, cifras, nombres ni fuentes que no aparezcan en el CONTEXTO.
4. Sé preciso y conciso. Si citas un dato, indica de qué fragmento proviene (p.ej. "según el \
fragmento de 'informe.pdf', página 3").
5. Si la pregunta es ambigua o parcialmente respondible, responde solo la parte que el \
CONTEXTO permite sustentar y aclara qué falta.
""".format(no_context_answer=NO_CONTEXT_ANSWER)


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
