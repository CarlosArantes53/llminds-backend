"""
Serviço de geração de respostas via Gemini API.

Inspirado no csv_translation do AcesseLibrasAI_goiasHUB,
adaptado para gerar respostas de dataset (prompt → response).
"""

from __future__ import annotations

import logging
from google import genai
from google.genai import types

from app.infrastructure.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _build_client() -> genai.Client:
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY não configurada no .env")
    return genai.Client(api_key=api_key)


def _get_safety_settings() -> list[types.SafetySetting]:
    return [
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        ),
    ]


DATASET_RESPONSE_SYSTEM_INSTRUCTION = """
Você é um assistente especializado em gerar respostas de alta qualidade para datasets de fine-tuning de LLMs.

Dado um prompt (pergunta ou instrução do usuário), gere uma resposta completa, precisa e bem estruturada.

Regras:
- A resposta deve ser informativa e diretamente relacionada ao prompt.
- Use linguagem clara e profissional.
- Se o prompt pedir uma explicação, forneça uma resposta didática.
- Se o prompt pedir uma ação (ex: código, tradução), execute-a.
- Mantenha a resposta concisa mas completa.
- Responda no mesmo idioma do prompt.
- NÃO inclua meta-comentários como "Aqui está a resposta:" — vá direto ao ponto.
""".strip()


async def generate_dataset_response(
    prompt_text: str,
    system_instruction: str | None = None,
) -> str:
    if not prompt_text.strip():
        raise ValueError("prompt_text não pode estar vazio")

    client = _build_client()
    model = settings.GEMINI_MODEL
    instruction = system_instruction or DATASET_RESPONSE_SYSTEM_INSTRUCTION
    safety = _get_safety_settings()

    logger.info(f"Gerando resposta via Gemini ({model}) para prompt: {prompt_text[:80]}...")

    try:
        resp = client.models.generate_content(
            model=model,
            contents=prompt_text.strip(),
            config=types.GenerateContentConfig(
                system_instruction=instruction,
                safety_settings=safety,
            ),
        )
        generated = resp.text.strip()
        logger.info(f"Resposta gerada com sucesso ({len(generated)} chars)")
        return generated

    except Exception as e:
        logger.error(f"Erro ao gerar resposta via Gemini: {e}")
        raise RuntimeError(f"Falha na geração via Gemini: {str(e)}") from e