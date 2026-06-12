from fastapi import HTTPException

from src.config import settings
from src.services.llm_client import LLMClient


def get_llm_client() -> LLMClient:
    api_key = settings.openai_api_key_value
    if not api_key:
        raise HTTPException(status_code=503, detail="OpenAI API key is not configured")
    return LLMClient(
        api_key=api_key,
        default_model=settings.openai_model,
    )
